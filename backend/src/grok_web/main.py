from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from grok_web.config import load_config
from grok_web.db import Database
from grok_web.mcp_client import MCPManager

app_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = load_config()
    db = Database(config.db_path)
    await db.connect()

    app_state["config"] = config
    app_state["db"] = db

    # Connect to MCP servers if configured
    if config.mcp_servers:
        mcp_manager = MCPManager()
        await mcp_manager.connect_all(config.mcp_servers)
        app_state["mcp_manager"] = mcp_manager

    yield

    if "mcp_manager" in app_state:
        await app_state["mcp_manager"].close_all()
    await db.close()
    app_state.clear()


app = FastAPI(title="grok-web", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from grok_web.routes.conversations import router as conv_router  # noqa: E402
from grok_web.routes.ws import router as ws_router  # noqa: E402

app.include_router(conv_router)
app.include_router(ws_router)
