from pathlib import Path

from grok_web.tools import ToolDefinition, ToolResult, ToolRegistry

DEFINITION = ToolDefinition(
    name="list_directory",
    description="List files and directories at a given path. Returns names with type indicators (/ for directories).",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to list. Defaults to current directory.",
            },
            "recursive": {
                "type": "boolean",
                "description": "List recursively (default false). Max depth 3 levels.",
            },
        },
        "required": [],
    },
)


async def handle(path: str = ".", recursive: bool = False) -> ToolResult:
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return ToolResult(output=f"Path not found: {path}", is_error=True)
        if not p.is_dir():
            return ToolResult(output=f"Not a directory: {path}", is_error=True)

        entries = []
        if recursive:
            _list_recursive(p, p, entries, depth=0, max_depth=3)
        else:
            for item in sorted(p.iterdir()):
                name = item.name + ("/" if item.is_dir() else "")
                entries.append(name)

        if not entries:
            return ToolResult(output="(empty directory)")

        return ToolResult(output="\n".join(entries))
    except PermissionError:
        return ToolResult(output=f"Permission denied: {path}", is_error=True)
    except Exception as e:
        return ToolResult(output=f"Error listing directory: {e}", is_error=True)


def _list_recursive(base: Path, current: Path, entries: list, depth: int, max_depth: int):
    if depth > max_depth:
        return
    try:
        for item in sorted(current.iterdir()):
            rel = item.relative_to(base)
            name = str(rel) + ("/" if item.is_dir() else "")
            entries.append(name)
            if item.is_dir() and not item.is_symlink():
                _list_recursive(base, item, entries, depth + 1, max_depth)
    except PermissionError:
        entries.append(f"{current.relative_to(base)}/ (permission denied)")


def register(registry: ToolRegistry):
    registry.register(DEFINITION, handle)
