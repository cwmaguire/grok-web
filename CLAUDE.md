# grok-web

Browser-based LLM chat tool using xAI's Grok models with tool use and MCP support.

## Quick Start

```bash
# Set API key in grok-web.json or env
export XAI_API_KEY=xai-...
./start.sh
# Open http://localhost:5173
```

## Architecture

- **Backend**: Python 3.12+ / FastAPI / `xai-sdk` (gRPC) / `aiosqlite`
- **Frontend**: React 19 / Vite / Zustand / CodeMirror 6 + vim
- **Model**: `grok-4-1-fast-reasoning` (configurable in grok-web.json)
- **Communication**: WebSocket for agent loop streaming, REST for conversation CRUD

## Project Structure

```
backend/src/grok_web/
  main.py          - FastAPI app with lifespan
  config.py        - Loads grok-web.json
  db.py            - SQLite schema + CRUD
  models.py        - Pydantic models, EventType enum
  agent.py         - Core agent loop (stream → tool call → execute → loop)
  llm.py           - xai_sdk wrapper (sync→async bridge via queue)
  mcp_client.py    - MCP server connections, namespaced tool dispatch
  tools/           - Built-in tools (read_file, write_file, search_replace, run_command, list_directory)
  routes/
    conversations.py - REST CRUD
    ws.py           - WebSocket agent loop endpoint

frontend/src/
  App.tsx           - CSS Grid 3-pane layout
  stores/chatStore.ts - Zustand state + WebSocket message routing
  components/
    OutputPane.tsx       - Rendered markdown messages
    InputPane.tsx        - CodeMirror + vim input
    IntermediatePane.tsx - Tool calls + thinking display
    ToolCallCard.tsx     - Collapsible tool call card
    Sidebar.tsx          - Conversation list
```

## Development

Backend: `cd backend && uv run uvicorn grok_web.main:app --reload --port 8000`
Frontend: `cd frontend && npx vite --port 5173`

Frontend proxies `/api` to backend via vite.config.ts.

## Key Patterns

- xai_sdk is synchronous gRPC; llm.py bridges to async via `asyncio.Queue` + `run_in_executor`
- MCP tools are namespaced as `{server}__{tool}` to avoid collisions
- Agent loop max 25 turns, cancellable between chunks and iterations
- SQLite stores full conversation history including tool calls/results
