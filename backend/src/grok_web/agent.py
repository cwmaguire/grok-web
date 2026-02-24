"""Core agent loop: stream LLM → detect tool calls → execute → loop."""

import json
import logging
from collections.abc import AsyncIterator

from grok_web.db import Database
from grok_web.llm import LLMClient, StreamChunk, ToolCallInfo
from grok_web.models import EventType, StreamEvent
from grok_web.tools import ToolRegistry

logger = logging.getLogger(__name__)

MAX_TURNS = 25


class AgentLoop:
    def __init__(self, llm: LLMClient, tools: ToolRegistry, db: Database):
        self._llm = llm
        self._tools = tools
        self._db = db
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    async def run(self, conversation_id: str, user_content: str) -> AsyncIterator[StreamEvent]:
        # Save user message
        await self._db.add_message(conversation_id, "user", content=user_content)

        # Load full history
        history = await self._db.get_messages(conversation_id)

        tool_schemas = self._tools.get_schemas()
        turn = 0

        while turn < MAX_TURNS:
            if self._cancelled:
                yield StreamEvent(type=EventType.CANCELLED)
                return

            turn += 1
            if turn > 1:
                yield StreamEvent(type=EventType.TURN_START, data={"turn_number": turn})

            # Stream LLM response
            accumulated_content = ""
            accumulated_reasoning = ""
            accumulated_tool_calls: list[ToolCallInfo] = []
            finish_reason = None

            try:
                async for chunk in self._llm.stream_response(history, tool_schemas):
                    if self._cancelled:
                        yield StreamEvent(type=EventType.CANCELLED)
                        return

                    if chunk.content:
                        accumulated_content += chunk.content
                        yield StreamEvent(
                            type=EventType.TEXT_DELTA,
                            data={"content": chunk.content},
                        )

                    if chunk.reasoning_content:
                        accumulated_reasoning += chunk.reasoning_content
                        yield StreamEvent(
                            type=EventType.THINKING,
                            data={"content": chunk.reasoning_content},
                        )

                    if chunk.finish_reason:
                        finish_reason = chunk.finish_reason
                        # Collect final tool calls from the finish chunk
                        if chunk.tool_calls:
                            accumulated_tool_calls = chunk.tool_calls

            except Exception as e:
                logger.exception("Agent stream error")
                yield StreamEvent(type=EventType.ERROR, data={"message": str(e)})
                return

            # Determine if we have tool calls
            has_tool_calls = finish_reason == "tool_calls" or (
                finish_reason and "tool" in str(finish_reason).lower()
            ) or len(accumulated_tool_calls) > 0

            if has_tool_calls and accumulated_tool_calls:
                # Save assistant message with tool calls
                tool_calls_data = [
                    {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                    for tc in accumulated_tool_calls
                ]
                await self._db.add_message(
                    conversation_id,
                    "assistant",
                    content=accumulated_content or None,
                    tool_calls=tool_calls_data,
                )

                # Execute each tool call
                for tc in accumulated_tool_calls:
                    if self._cancelled:
                        yield StreamEvent(type=EventType.CANCELLED)
                        return

                    # Parse arguments
                    try:
                        args = json.loads(tc.arguments) if tc.arguments else {}
                    except json.JSONDecodeError:
                        args = {}

                    yield StreamEvent(
                        type=EventType.TOOL_CALL,
                        data={"id": tc.id, "name": tc.name, "arguments": args},
                    )

                    # Execute
                    result = await self._tools.execute(tc.name, args)

                    yield StreamEvent(
                        type=EventType.TOOL_RESULT,
                        data={
                            "id": tc.id,
                            "name": tc.name,
                            "result": result.output,
                            "is_error": result.is_error,
                        },
                    )

                    # Save tool result message
                    await self._db.add_message(
                        conversation_id,
                        "tool",
                        content=result.output,
                        tool_use_id=tc.id,
                        is_error=result.is_error,
                    )

                # Reload history with tool results and continue loop
                history = await self._db.get_messages(conversation_id)
                continue

            else:
                # No tool calls - save assistant message and we're done
                if accumulated_content:
                    await self._db.add_message(
                        conversation_id, "assistant", content=accumulated_content
                    )
                yield StreamEvent(type=EventType.DONE)
                return

        # Hit max turns
        yield StreamEvent(
            type=EventType.ERROR,
            data={"message": f"Agent loop exceeded {MAX_TURNS} turns"},
        )
