"""MCP server connections, tool discovery, and namespaced dispatch."""

import asyncio
import logging
from typing import Awaitable, Callable

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from grok_web.config import MCPServerConfig
from grok_web.tools import ToolDefinition, ToolResult

logger = logging.getLogger(__name__)

SEPARATOR = "__"


class MCPConnection:
    """A single connection to an MCP server."""

    def __init__(self, name: str, config: MCPServerConfig):
        self.name = name
        self.config = config
        self.session: ClientSession | None = None
        self.tools: list[dict] = []
        self._ctx_stack = None

    async def connect(self):
        server_params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
            env=self.config.env or None,
        )

        read_stream, write_stream = await self._start_stdio(server_params)
        self.session = ClientSession(read_stream, write_stream)
        await self.session.initialize()

        # Discover tools
        result = await self.session.list_tools()
        self.tools = []
        for tool in result.tools:
            self.tools.append({
                "name": f"{self.name}{SEPARATOR}{tool.name}",
                "description": tool.description or "",
                "parameters": tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                "original_name": tool.name,
            })
        logger.info(f"MCP server '{self.name}': discovered {len(self.tools)} tools")

    async def _start_stdio(self, params: StdioServerParameters):
        """Start stdio MCP server process and return streams."""
        # Use the mcp SDK's stdio_client context manager
        # We need to manage the lifecycle ourselves
        self._cm = stdio_client(params)
        read_stream, write_stream = await self._cm.__aenter__()
        return read_stream, write_stream

    async def call_tool(self, original_name: str, arguments: dict) -> ToolResult:
        if not self.session:
            return ToolResult(output="MCP server not connected", is_error=True)
        try:
            result = await self.session.call_tool(original_name, arguments)
            # Combine text content from result
            output_parts = []
            for content in result.content:
                if hasattr(content, 'text'):
                    output_parts.append(content.text)
                else:
                    output_parts.append(str(content))
            return ToolResult(
                output="\n".join(output_parts) if output_parts else "(no output)",
                is_error=result.isError if hasattr(result, 'isError') else False,
            )
        except Exception as e:
            logger.exception(f"MCP tool call failed: {original_name}")
            return ToolResult(output=f"MCP error: {e}", is_error=True)

    async def close(self):
        if self._cm:
            try:
                await self._cm.__aexit__(None, None, None)
            except Exception:
                pass


class MCPManager:
    """Manages all MCP server connections."""

    def __init__(self):
        self._connections: dict[str, MCPConnection] = {}

    async def connect_all(self, servers: dict[str, MCPServerConfig]):
        for name, config in servers.items():
            conn = MCPConnection(name, config)
            try:
                await conn.connect()
                self._connections[name] = conn
            except Exception:
                logger.exception(f"Failed to connect to MCP server: {name}")

    def get_tool_schemas(self) -> list[dict]:
        schemas = []
        for conn in self._connections.values():
            for tool in conn.tools:
                schemas.append({
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                })
        return schemas

    def make_handler(self, namespaced_name: str) -> Callable[..., Awaitable[ToolResult]]:
        """Create an async handler for a namespaced MCP tool."""
        parts = namespaced_name.split(SEPARATOR, 1)
        if len(parts) != 2:
            async def _err(**kwargs):
                return ToolResult(output=f"Invalid MCP tool name: {namespaced_name}", is_error=True)
            return _err

        server_name, original_name = parts
        conn = self._connections.get(server_name)
        if not conn:
            async def _err(**kwargs):
                return ToolResult(output=f"MCP server not found: {server_name}", is_error=True)
            return _err

        async def handler(**kwargs):
            return await conn.call_tool(original_name, kwargs)
        return handler

    async def close_all(self):
        for conn in self._connections.values():
            await conn.close()
        self._connections.clear()
