"""WebSocket endpoint for the agent loop."""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from grok_web.agent import AgentLoop
from grok_web.llm import LLMClient
from grok_web.tools import create_registry

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/api/ws/{conversation_id}")
async def websocket_agent(websocket: WebSocket, conversation_id: str):
    from grok_web.main import app_state

    db = app_state["db"]
    config = app_state["config"]

    # Verify conversation exists
    conv = await db.get_conversation(conversation_id)
    if not conv:
        await websocket.close(code=4004, reason="Conversation not found")
        return

    await websocket.accept()

    llm = LLMClient(config)
    tools = create_registry()

    # Merge MCP tools if available
    mcp_manager = app_state.get("mcp_manager")
    if mcp_manager:
        for schema in mcp_manager.get_tool_schemas():
            from grok_web.tools import ToolDefinition
            tools.register(
                ToolDefinition(
                    name=schema["name"],
                    description=schema["description"],
                    parameters=schema["parameters"],
                ),
                mcp_manager.make_handler(schema["name"]),
            )

    active_loop: AgentLoop | None = None

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)

            if msg.get("type") == "interrupt":
                if active_loop:
                    active_loop.cancel()
                    active_loop = None
                continue

            if msg.get("type") == "user_message":
                content = msg.get("content", "").strip()
                if not content:
                    continue

                agent = AgentLoop(llm, tools, db)
                active_loop = agent

                try:
                    async for event in agent.run(conversation_id, content):
                        await websocket.send_json(event.to_ws())
                except Exception as e:
                    logger.exception("Agent loop error")
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": str(e)},
                    })
                finally:
                    active_loop = None

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {conversation_id}")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
    finally:
        if active_loop:
            active_loop.cancel()
