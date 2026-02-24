from pathlib import Path

from grok_web.tools import ToolDefinition, ToolResult, ToolRegistry

DEFINITION = ToolDefinition(
    name="read_file",
    description="Read the contents of a file. Returns the file content as text. Optionally read a specific line range.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute or relative path to the file to read",
            },
            "offset": {
                "type": "integer",
                "description": "Starting line number (1-based). Optional.",
            },
            "limit": {
                "type": "integer",
                "description": "Number of lines to read from offset. Optional.",
            },
        },
        "required": ["path"],
    },
)


async def handle(path: str, offset: int | None = None, limit: int | None = None) -> ToolResult:
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return ToolResult(output=f"File not found: {path}", is_error=True)
        if not p.is_file():
            return ToolResult(output=f"Not a file: {path}", is_error=True)

        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines(keepends=True)

        if offset is not None or limit is not None:
            start = max(0, (offset or 1) - 1)
            end = start + (limit or len(lines))
            lines = lines[start:end]
            # Add line numbers
            numbered = []
            for i, line in enumerate(lines, start=start + 1):
                numbered.append(f"{i:6d}\t{line}")
            return ToolResult(output="".join(numbered))

        # Add line numbers for full file too
        numbered = []
        for i, line in enumerate(lines, start=1):
            numbered.append(f"{i:6d}\t{line}")
        return ToolResult(output="".join(numbered))
    except Exception as e:
        return ToolResult(output=f"Error reading file: {e}", is_error=True)


def register(registry: ToolRegistry):
    registry.register(DEFINITION, handle)
