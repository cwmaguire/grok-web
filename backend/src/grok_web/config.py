import json
import os
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class MCPServerConfig:
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class Config:
    api_key: str
    model: str
    db_path: str
    mcp_servers: dict[str, MCPServerConfig]


def load_config(config_path: str | None = None) -> Config:
    if config_path is None:
        config_path = os.environ.get(
            "GROK_WEB_CONFIG",
            str(Path(__file__).resolve().parents[3] / "grok-web.json"),
        )

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(path) as f:
        raw = json.load(f)

    api_key = raw.get("apiKey") or os.environ.get("XAI_API_KEY", "")
    if not api_key:
        raise ValueError("API key must be set in grok-web.json or XAI_API_KEY env var")

    model = raw.get("model", "grok-4-1-fast-reasoning")
    db_path = raw.get("dbPath", "./data/grok-web.db")

    # Resolve db_path relative to config file location
    if not Path(db_path).is_absolute():
        db_path = str(path.parent / db_path)

    mcp_servers = {}
    for name, server_raw in raw.get("mcpServers", {}).items():
        mcp_servers[name] = MCPServerConfig(
            command=server_raw["command"],
            args=server_raw.get("args", []),
            env=server_raw.get("env", {}),
        )

    return Config(
        api_key=api_key,
        model=model,
        db_path=db_path,
        mcp_servers=mcp_servers,
    )
