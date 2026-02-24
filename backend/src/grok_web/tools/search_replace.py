from pathlib import Path

from grok_web.tools import ToolDefinition, ToolResult, ToolRegistry

DEFINITION = ToolDefinition(
    name="search_replace",
    description="Search for an exact string in a file and replace it with new content. The old_string must match exactly (including whitespace and indentation).",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to modify",
            },
            "old_string": {
                "type": "string",
                "description": "The exact string to search for",
            },
            "new_string": {
                "type": "string",
                "description": "The string to replace it with",
            },
            "replace_all": {
                "type": "boolean",
                "description": "Replace all occurrences (default false, replaces first only)",
            },
        },
        "required": ["path", "old_string", "new_string"],
    },
)


async def handle(
    path: str, old_string: str, new_string: str, replace_all: bool = False
) -> ToolResult:
    try:
        p = Path(path).expanduser().resolve()
        if not p.exists():
            return ToolResult(output=f"File not found: {path}", is_error=True)

        content = p.read_text(encoding="utf-8")

        if old_string not in content:
            return ToolResult(
                output=f"String not found in {path}. Make sure the old_string matches exactly.",
                is_error=True,
            )

        if replace_all:
            count = content.count(old_string)
            new_content = content.replace(old_string, new_string)
        else:
            count = 1
            new_content = content.replace(old_string, new_string, 1)

        p.write_text(new_content, encoding="utf-8")
        return ToolResult(output=f"Replaced {count} occurrence(s) in {p}")
    except Exception as e:
        return ToolResult(output=f"Error in search/replace: {e}", is_error=True)


def register(registry: ToolRegistry):
    registry.register(DEFINITION, handle)
