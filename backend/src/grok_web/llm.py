"""Wrapper around xai_sdk for chat completions with streaming and tool use."""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from xai_sdk import Client
from xai_sdk.chat import user, system, assistant, tool as make_tool, tool_result

from grok_web.config import Config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a powerful AI coding assistant running in a browser-based development tool called grok-web. You have access to tools that let you interact with the local filesystem and run shell commands.

When the user asks you to perform tasks:
- Use the available tools to read files, write files, search/replace in files, list directories, and run commands
- Be thorough and precise in your tool usage
- Show your work by explaining what you're doing

You can make multiple tool calls in sequence to accomplish complex tasks."""


@dataclass
class ToolCallInfo:
    id: str
    name: str
    arguments: str  # JSON string


@dataclass
class StreamChunk:
    """A chunk from the LLM stream."""
    content: str | None = None
    reasoning_content: str | None = None
    tool_calls: list[ToolCallInfo] = field(default_factory=list)
    finish_reason: str | None = None


def _build_tool_definitions(tool_schemas: list[dict]) -> list:
    """Convert our tool schemas into xai_sdk tool objects."""
    tools = []
    for schema in tool_schemas:
        tools.append(make_tool(
            name=schema["name"],
            description=schema["description"],
            parameters=schema["parameters"],
        ))
    return tools


def _build_messages(history: list[dict]) -> list:
    """Convert stored message dicts back to xai_sdk message objects."""
    msgs = [system(SYSTEM_PROMPT)]
    for msg in history:
        role = msg["role"]
        if role == "user":
            msgs.append(user(msg["content"]))
        elif role == "assistant":
            if msg.get("tool_calls"):
                # Assistant message with tool calls - append as assistant with content
                msgs.append(assistant(msg.get("content") or ""))
            else:
                msgs.append(assistant(msg.get("content") or ""))
        elif role == "tool":
            msgs.append(tool_result(
                result=msg["content"] or "",
                tool_call_id=msg.get("tool_use_id", ""),
            ))
    return msgs


class LLMClient:
    def __init__(self, config: Config):
        self._config = config
        self._client = Client(api_key=config.api_key)

    def close(self):
        pass

    async def stream_response(
        self,
        history: list[dict],
        tool_schemas: list[dict],
    ) -> AsyncIterator[StreamChunk]:
        """Stream a response from the LLM, yielding chunks as they arrive.

        Runs the synchronous SDK stream in a thread to avoid blocking.
        Uses an asyncio.Queue to bridge sync iteration to async iteration.
        """
        queue: asyncio.Queue[StreamChunk | None] = asyncio.Queue()

        def _run_stream():
            try:
                messages = _build_messages(history)
                tools = _build_tool_definitions(tool_schemas) if tool_schemas else None

                kwargs = {
                    "model": self._config.model,
                    "messages": messages,
                }
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"

                chat = self._client.chat.create(**kwargs)

                final_response = None
                for response, chunk in chat.stream():
                    final_response = response
                    sc = StreamChunk()

                    if chunk.content:
                        sc.content = chunk.content

                    if chunk.reasoning_content:
                        sc.reasoning_content = chunk.reasoning_content

                    if chunk.tool_calls:
                        for tc in chunk.tool_calls:
                            sc.tool_calls.append(ToolCallInfo(
                                id=tc.id,
                                name=tc.function.name if tc.function else "",
                                arguments=tc.function.arguments if tc.function else "",
                            ))

                    queue.put_nowait(sc)

                # Send final chunk with finish reason
                if final_response:
                    final_chunk = StreamChunk(finish_reason=final_response.finish_reason)
                    # Include accumulated tool calls from the full response
                    if final_response.tool_calls:
                        for tc in final_response.tool_calls:
                            final_chunk.tool_calls.append(ToolCallInfo(
                                id=tc.id,
                                name=tc.function.name if tc.function else "",
                                arguments=tc.function.arguments if tc.function else "",
                            ))
                    queue.put_nowait(final_chunk)

            except Exception as e:
                logger.exception("LLM stream error")
                queue.put_nowait(StreamChunk(finish_reason=f"error: {e}"))
            finally:
                queue.put_nowait(None)  # Sentinel

        # Run sync stream in thread
        loop = asyncio.get_event_loop()
        task = loop.run_in_executor(None, _run_stream)

        try:
            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                yield chunk
        finally:
            await task
