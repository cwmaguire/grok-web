# grok-web

A browser-based LLM chat tool using xAI's Grok models — a "Claude Code clone" that trades the shell for a three-pane browser UI with vim keybindings, while giving the LLM full access to the local machine via built-in tools and configurable MCP servers.

## Motivation

Shell-based AI coding assistants are painful for editing and hide intermediate LLM activity. grok-web exposes everything: streaming text output in one pane, your vim-enabled input in another, and all tool calls, thinking tokens, and execution results in a dedicated activity pane. It's a local-only dev tool — it runs on your machine because it needs access to your machine.

## Quick Start

```bash
# 1. Set your xAI API key
export XAI_API_KEY=xai-...
# Or edit grok-web.json directly: "apiKey": "xai-..."

# 2. Launch both servers
./start.sh

# 3. Open http://localhost:5173
```

Requires Python 3.12+, Node.js 18+, and [uv](https://docs.astral.sh/uv/).

## Architecture

```
┌──────────┬───────────────────┬───────────────────┐
│          │   Output Pane     │                   │
│ Sidebar  │   (markdown)      │  Activity Pane    │
│          │                   │  (tool calls,     │
│ convos   ├───────────────────┤   thinking,       │
│          │   Input Pane      │   status)         │
│          │   (vim + CM6)     │                   │
└──────────┴───────────────────┴───────────────────┘
```

- **Backend**: Python 3.12+ / FastAPI / `xai-sdk` (native gRPC) / `aiosqlite`
- **Frontend**: React 19 / Vite / Zustand / CodeMirror 6 + `@replit/codemirror-vim` / `react-markdown`
- **Model**: `grok-4-1-fast-reasoning` (configurable)
- **Comms**: WebSocket for agent loop streaming + interrupts, REST for conversation CRUD

## How It Works

1. You type in the input pane (vim keybindings, Ctrl+Enter to send)
2. Your message hits the backend via WebSocket
3. The agent loop streams the LLM response, routing `text_delta` events to the output pane and `thinking`/`tool_call`/`tool_result` events to the activity pane
4. If the LLM makes tool calls, the agent executes them and gives the results back to the LLM for another turn
5. The loop continues until the LLM responds with text only (no tool calls), or hits the 25-turn limit
6. You can interrupt at any time with the interrupt button

## Built-in Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents with optional line range |
| `write_file` | Write/create files with parent directory creation |
| `search_replace` | Exact string replacement in files |
| `run_command` | Execute shell commands (120s default timeout) |
| `list_directory` | List files/directories, optionally recursive |

## MCP Server Support

Configure MCP servers in `grok-web.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "env": {}
    }
  }
}
```

MCP tools are namespaced as `{server}__{tool}` to avoid collisions between servers.

## Configuration

`grok-web.json` in the project root:

```json
{
  "apiKey": "xai-...",
  "model": "grok-4-1-fast-reasoning",
  "dbPath": "./data/grok-web.db",
  "mcpServers": {}
}
```

The API key can also be set via `XAI_API_KEY` environment variable (takes precedence over the config file).

## Project Structure

```
grok-web/
├── grok-web.json              # Config
├── start.sh                   # Launches backend + frontend
├── backend/
│   ├── pyproject.toml
│   └── src/grok_web/
│       ├── main.py            # FastAPI app + lifespan
│       ├── config.py          # Config loading
│       ├── db.py              # SQLite schema + CRUD
│       ├── models.py          # Pydantic models, event types
│       ├── agent.py           # Core agent loop
│       ├── llm.py             # xai-sdk wrapper (sync→async bridge)
│       ├── mcp_client.py      # MCP server management
│       ├── tools/             # 5 built-in tools
│       └── routes/            # REST + WebSocket endpoints
└── frontend/
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── App.tsx            # Three-pane CSS Grid layout
        ├── stores/chatStore.ts # Zustand + WebSocket routing
        └── components/        # OutputPane, InputPane, IntermediatePane, etc.
```

## Development

Run servers independently:

```bash
# Backend
cd backend && uv run uvicorn grok_web.main:app --reload --port 8000

# Frontend (proxies /api to backend)
cd frontend && npx vite --port 5173
```

## WebSocket Protocol

Client → Server:
- `{"type": "user_message", "content": "..."}` — start agent loop
- `{"type": "interrupt"}` — cancel active loop

Server → Client:
- `text_delta` — streaming text (output pane)
- `thinking` — reasoning tokens (activity pane)
- `tool_call` — tool invocation (activity pane)
- `tool_result` — tool output (activity pane)
- `turn_start` — new LLM turn after tool execution
- `done` / `cancelled` / `error` — terminal events
