# grok-web — Implementation Plan (v1)

## Problem Statement

Shell-based AI coding assistants (Claude Code, aider, etc.) suffer from two UX problems: editing in a terminal is painful, and intermediate LLM activity (tool calls, thinking, multi-turn loops) is hidden or crudely displayed. grok-web is a browser-based alternative that exposes everything in a three-pane UI with vim keybindings, while giving the LLM full access to the local machine.

This is a local-only dev tool — not a hosted product. It runs on your machine because it needs to read/write your files and execute your commands.

## Technology Choices and Rationale

### Backend: Python 3.12+ / FastAPI

FastAPI is the dominant choice for Python LLM chat backends. Open WebUI (57k stars, the closest architectural precedent) uses FastAPI. It provides native async/await, first-class WebSocket support, and auto-generated OpenAPI docs. Flask lacks native async; Django Channels is too heavyweight for a local dev tool.

### Frontend: React 19 / Vite

React was chosen over SvelteKit (used by Open WebUI) because React has the largest ecosystem and the most LLM training data — important since this project is built with AI assistance. LibreChat, LobeChat, and AnythingLLM all use React. SvelteKit showed 300% year-over-year growth but React's dominance in training data was the deciding factor.

### xai-sdk (native gRPC) over OpenAI-compatible API

The native `xai-sdk` gives access to xAI-specific features (remote MCP, X search, server-side code interpreter) and has a cleaner streaming API — `chat.stream()` yields `(response, chunk)` tuples with structured tool call data. The OpenAI-compatible REST API has more tutorials and familiarity but loses access to xAI-specific features. The OpenAI REST API remains a fallback if the gRPC SDK causes issues.

### CodeMirror 6 + @replit/codemirror-vim

Two options were evaluated: CodeMirror 6 with `@replit/codemirror-vim` (maintained by Replit) and Monaco Editor with `monaco-vim`. CodeMirror 6 wins on bundle size (~300KB vs ~5-10MB for Monaco), mobile support, accessibility, and active maintenance. Sourcegraph's migration from Monaco to CodeMirror showed a 43% reduction in JavaScript bundle size. Monaco is designed for full IDE scenarios and brings unnecessary weight for a chat input.

### Zustand for State Management

Lightweight, minimal boilerplate, works well for this use case. LobeChat uses Zustand. Avoids the ceremony of Redux or the experimental status of Recoil.

### SQLite (aiosqlite) for Persistence

Simplest option for a local app — no separate database server. Conversations persist across sessions. The xAI API offers server-side conversation storage (`store_messages=True`) but local SQLite gives full control over data retention without depending on xAI's infrastructure.

### UV for Python Package Management

The modern fast option over poetry or pip+venv.

### Single WebSocket (not SSE + WebSocket)

SSE is the industry standard for LLM streaming (used by OpenAI, Anthropic APIs). It auto-reconnects, works through proxies/CDNs, and scales horizontally. However, SSE is unidirectional — a separate WebSocket would be needed for the interrupt signal. For a local-only dev tool, maintaining two connection types isn't worth the marginal benefits. A single WebSocket carries streaming output and interrupt signals.

## Architecture Decisions

### Output Routing: By Event Type, Not Tag Parsing

User-facing output and intermediate activity are routed by event type. `text_delta` events go to the output pane. `tool_call`, `tool_result`, and `thinking` events go to the activity pane. This is reliable because it does not depend on the LLM following formatting instructions — the xAI SDK cleanly separates text content from tool calls in its response objects. No XML tag parsing or heuristics.

### MCP Tool Namespacing

MCP tools are prefixed `{server_name}__{tool_name}` to avoid collisions when multiple MCP servers expose tools with the same name. The prefix is stripped before calling the actual MCP server.

### Fully Async Backend

`AsyncClient`, `aiosqlite`, `asyncio.create_subprocess_shell` throughout. The agent loop may run long-lived tool executions (shell commands with 120-second timeouts) while simultaneously streaming results over WebSocket. Blocking the event loop would break the streaming experience.

The xai-sdk is synchronous (gRPC-based), so `llm.py` bridges to async via `asyncio.Queue` and `run_in_executor` — the sync stream runs in a thread and feeds chunks through an async queue.

### No Tool Approval Model

Unlike Claude Code which asks permission before destructive operations, grok-web executes all tools automatically. This simplifies the agent loop (no client-side approval flow) and matches the "always run with wide-open permissions" workflow.

### Agent Loop Design

```
user sends message → append to chat history → enter loop:
  1. Stream LLM response, yielding text_delta/thinking events
  2. If response has tool_calls:
     - Yield tool_call event for each
     - Execute tool (built-in or MCP)
     - Yield tool_result event
     - Append tool results to chat history
     - Continue loop (LLM gets another turn)
  3. If no tool_calls: yield done event, exit loop

  Cancellation: _cancelled flag checked between chunks and between loop iterations
  Max turns: 25
```

## Communication Protocol

### REST Endpoints

- `POST /api/conversations` — create conversation
- `GET /api/conversations` — list all conversations
- `GET /api/conversations/:id` — get single conversation
- `PATCH /api/conversations/:id` — update title
- `DELETE /api/conversations/:id` — delete conversation
- `GET /api/conversations/:id/messages` — get message history

### WebSocket (`ws://localhost:8000/api/ws/:conversation_id`)

Client → Server:
- `{"type": "user_message", "content": "..."}` — starts agent loop
- `{"type": "interrupt"}` — cancels active agent loop

Server → Client:
- `{"type": "text_delta", "data": {"content": "..."}}` — output pane
- `{"type": "thinking", "data": {"content": "..."}}` — activity pane
- `{"type": "tool_call", "data": {"id", "name", "arguments"}}` — activity pane
- `{"type": "tool_result", "data": {"id", "name", "result", "is_error"}}` — activity pane
- `{"type": "turn_start", "data": {"turn_number": N}}` — new LLM turn
- `{"type": "done"}` / `{"type": "cancelled"}` / `{"type": "error", "data": {"message"}}`

## Data Model

### SQLite Schema

```sql
conversations(id TEXT PK, title TEXT, created_at TEXT, updated_at TEXT)
messages(id TEXT PK, conversation_id TEXT FK, role TEXT, content TEXT,
         tool_calls TEXT, tool_use_id TEXT, is_error INT, created_at TEXT, seq INT)
```

Messages use a `seq` column for ordering rather than relying on timestamps, since multiple messages can be created in rapid succession during tool execution.

### Config Format (`grok-web.json`)

```json
{
  "apiKey": "xai-...",
  "model": "grok-4-1-fast-reasoning",
  "dbPath": "./data/grok-web.db",
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "env": {}
    }
  }
}
```

## Implementation Phases

### Phase 1: Skeleton + Backend Core
1. Create directory structure, `pyproject.toml`, `grok-web.json`
2. `config.py` — parse config, handle env vars
3. `db.py` — SQLite schema, all CRUD methods
4. `main.py` — FastAPI app with lifespan, CORS
5. `routes/conversations.py` — REST CRUD
6. Verify: `uv run uvicorn grok_web.main:app --reload`, test with curl

### Phase 2: LLM + Agent Loop + Tools
7. `models.py` — Pydantic models, EventType enum, StreamEvent
8. `llm.py` — xai_sdk wrapper (init_chat, stream, sync→async bridge)
9. `tools/` — ToolRegistry + 5 built-in tools (read_file, write_file, search_replace, run_command, list_directory)
10. `agent.py` — the core agent loop
11. `routes/ws.py` — WebSocket endpoint bridging agent loop to client
12. Verify: connect with websocat, send message, confirm streaming + tool execution

### Phase 3: Frontend
13. Scaffold React app with Vite + TypeScript
14. `App.tsx` — CSS Grid three-pane layout with sidebar
15. `chatStore.ts` — Zustand store with all state + WebSocket routing
16. `OutputPane.tsx` — react-markdown + syntax highlighting
17. `InputPane.tsx` — CodeMirror 6 + vim + Ctrl+Enter submit
18. `IntermediatePane.tsx` + `ToolCallCard.tsx`
19. `Sidebar.tsx` — conversation list with create/delete
20. Verify: full end-to-end flow in browser

### Phase 4: MCP + Launch Script
21. `mcp_client.py` — connect to configured servers, discover tools, namespaced dispatch
22. Merge MCP tools into agent (pass combined definitions to LLM)
23. `start.sh` — launches both servers with cleanup trap
24. `CLAUDE.md` for the project

## Scope — v1 vs Future

### In Scope (v1)
- Three-pane browser UI with vim input
- Streaming chat with single Grok model
- Agent loop with tool use (5 built-in tools)
- Interrupt button
- SQLite conversation persistence
- MCP server configuration and tool discovery
- Launch script for dev use

### Deferred
- Multi-agent / sub-agent orchestration
- Package manager integration (brew/apt install)
- Advanced MCP features (server-side MCP via xAI)
- Authentication / multi-user support
- Production deployment / bundling
- File upload / image support
- Conversation search
- Custom system prompts per conversation

## Verification Checklist

1. `./start.sh` starts both servers, open `http://localhost:5173`
2. Type a message → streaming text appears in output pane
3. Ask LLM to read a file → tool_call/tool_result in activity pane
4. Ask LLM to run a shell command → execution and output
5. Click interrupt during a long response → cancellation
6. Refresh page → conversation persists from SQLite
7. Configure an MCP server → its tools are discovered and usable
