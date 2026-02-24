from pathlib import Path

from grok_web.tools import ToolDefinition, ToolResult, ToolRegistry

DEFINITION = ToolDefinition(
    name="write_file",
    description="Write content to a file. Creates the file and parent directories if they don't exist. Overwrites existing content.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute or relative path to the file to write",
            },
            "content": {
                "type": "string",
                "description": "The content to write to the file",
            },
        },
        "required": ["path", "content"],
    },
)


async def handle(path: str, content: str) -> ToolResult:
    try:
        p = Path(path).expanduser().resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return ToolResult(output=f"Successfully wrote {len(content)} bytes to {p}")
    except Exception as e:
        return ToolResult(output=f"Error writing file: {e}", is_error=True)


def register(registry: ToolRegistry):
    registry.register(DEFINITION, handle)
