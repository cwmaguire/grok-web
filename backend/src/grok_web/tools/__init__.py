"""Tool registry and base types for built-in tools."""

import json
import logging
from dataclasses import dataclass
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict  # JSON Schema


@dataclass
class ToolResult:
    output: str
    is_error: bool = False


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, tuple[ToolDefinition, Callable[..., Awaitable[ToolResult]]]] = {}

    def register(self, definition: ToolDefinition, handler: Callable[..., Awaitable[ToolResult]]):
        self._tools[definition.name] = (definition, handler)

    def get_schemas(self) -> list[dict]:
        return [
            {
                "name": defn.name,
                "description": defn.description,
                "parameters": defn.parameters,
            }
            for defn, _ in self._tools.values()
        ]

    async def execute(self, name: str, arguments: dict) -> ToolResult:
        if name not in self._tools:
            return ToolResult(output=f"Unknown tool: {name}", is_error=True)
        _, handler = self._tools[name]
        try:
            return await handler(**arguments)
        except Exception as e:
            logger.exception(f"Tool {name} failed")
            return ToolResult(output=f"Error executing {name}: {e}", is_error=True)


def create_registry() -> ToolRegistry:
    """Create a registry with all built-in tools registered."""
    from grok_web.tools.read_file import register
    from grok_web.tools.write_file import register as register_write
    from grok_web.tools.search_replace import register as register_sr
    from grok_web.tools.run_command import register as register_cmd
    from grok_web.tools.list_directory import register as register_ls

    registry = ToolRegistry()
    register(registry)
    register_write(registry)
    register_sr(registry)
    register_cmd(registry)
    register_ls(registry)
    return registry
