"""MCP Manager - Manages connections to MCP servers using the official SDK."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from dsagent.tools.config import MCPConfig, MCPServerConfig

# Check if MCP is available
try:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.types import Tool as MCPTool

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    ClientSession = None
    MCPTool = None
    streamablehttp_client = None  # type: ignore

logger = logging.getLogger(__name__)


class MCPNotAvailableError(Exception):
    """Raised when MCP functionality is requested but mcp package is not installed."""

    pass


class ToolNotFoundError(Exception):
    """Raised when a requested tool is not found in any MCP server."""

    pass


@dataclass
class MCPServerConnection:
    """Represents an active connection to an MCP server."""

    name: str
    config: MCPServerConfig
    session: Optional[Any] = None  # ClientSession
    tools: Dict[str, Dict] = field(default_factory=dict)
    _context_managers: List[Any] = field(default_factory=list)

    @property
    def is_connected(self) -> bool:
        """Check if the server is connected."""
        return self.session is not None


class MCPManager:
    """Manages connections to multiple MCP servers.

    This class uses the official MCP Python SDK to connect to MCP servers
    and expose their tools to the LLM.

    Example:
        ```python
        # From YAML config
        manager = MCPManager.from_yaml("~/.dsagent/mcp.yaml")
        manager.connect_all_sync()  # Synchronous connection

        # Get tools for LLM
        tools = manager.get_tools_for_llm()

        # Execute a tool (synchronous)
        result = manager.execute_tool_sync("web_search", {"query": "python"})

        # Cleanup
        manager.disconnect_all_sync()
        ```

    Example YAML config:
        ```yaml
        servers:
          - name: web_search
            command: ["npx", "-y", "@modelcontextprotocol/server-brave-search"]
            env:
              BRAVE_API_KEY: "${BRAVE_API_KEY}"
        ```
    """

    def __init__(self, config: Optional[MCPConfig] = None):
        """Initialize the MCP Manager.

        Args:
            config: MCP configuration. If None, no servers will be configured.
        """
        if not MCP_AVAILABLE:
            logger.warning(
                "MCP package not installed. Install with: pip install 'datascience-agent[mcp]'"
            )

        self.config = config or MCPConfig()
        self._connections: Dict[str, MCPServerConnection] = {}
        self._tools_cache: Dict[str, Dict[str, Any]] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[Any] = None

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "MCPManager":
        """Create MCPManager from a YAML configuration file.

        Args:
            path: Path to the YAML configuration file

        Returns:
            MCPManager instance
        """
        config = MCPConfig.from_yaml(path)
        return cls(config)

    @classmethod
    def from_dict(cls, data: Dict) -> "MCPManager":
        """Create MCPManager from a dictionary.

        Args:
            data: Dictionary with server configurations

        Returns:
            MCPManager instance
        """
        config = MCPConfig.from_dict(data)
        return cls(config)

    @property
    def is_available(self) -> bool:
        """Check if MCP functionality is available."""
        return MCP_AVAILABLE

    @property
    def connected_servers(self) -> List[str]:
        """Get list of connected server names."""
        return [name for name, conn in self._connections.items() if conn.is_connected]

    @property
    def available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return list(self._tools_cache.keys())

    async def connect_all(self) -> None:
        """Connect to all configured MCP servers."""
        if not MCP_AVAILABLE:
            raise MCPNotAvailableError(
                "MCP package not installed. Install with: pip install 'datascience-agent[mcp]'"
            )

        for server_config in self.config.get_enabled_servers():
            try:
                await self._connect_server(server_config)
                logger.info(f"Connected to MCP server: {server_config.name}")
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {server_config.name}: {e}")

    async def _connect_server(self, config: MCPServerConfig) -> None:
        """Connect to a single MCP server.

        Args:
            config: Server configuration
        """
        connection = MCPServerConnection(name=config.name, config=config)

        if config.transport == "stdio":
            await self._connect_stdio(connection)
        elif config.transport == "http":
            await self._connect_http(connection)
        else:
            raise ValueError(f"Unknown transport type: {config.transport}")

        # Discover tools
        await self._discover_tools(connection)

        self._connections[config.name] = connection

    async def _connect_stdio(self, connection: MCPServerConnection) -> None:
        """Connect to an MCP server via stdio transport.

        Args:
            connection: Server connection object
        """
        config = connection.config

        if not config.command:
            raise ValueError(f"No command specified for stdio server: {config.name}")

        # Resolve environment variables
        env = config.resolve_env()

        # Create server parameters
        params = StdioServerParameters(
            command=config.command[0],
            args=config.command[1:] if len(config.command) > 1 else [],
            env=env if env else None,
        )

        # Create stdio client context manager
        stdio_cm = stdio_client(params)
        read, write = await stdio_cm.__aenter__()
        connection._context_managers.append(stdio_cm)

        # Create session
        session = ClientSession(read, write)
        await session.__aenter__()
        connection._context_managers.append(session)

        # Initialize the session
        await session.initialize()

        connection.session = session

    async def _connect_http(self, connection: MCPServerConnection) -> None:
        """Connect to an MCP server via HTTP transport.

        Args:
            connection: Server connection object
        """
        config = connection.config

        if not config.url:
            raise ValueError(f"No URL specified for HTTP server: {config.name}")

        # Create HTTP client context manager
        http_cm = streamablehttp_client(config.url)
        read, write, _ = await http_cm.__aenter__()
        connection._context_managers.append(http_cm)

        # Create session
        session = ClientSession(read, write)
        await session.__aenter__()
        connection._context_managers.append(session)

        # Initialize the session
        await session.initialize()

        connection.session = session

    async def _discover_tools(self, connection: MCPServerConnection) -> None:
        """Discover available tools from an MCP server.

        Args:
            connection: Server connection object
        """
        if not connection.session:
            return

        result = await connection.session.list_tools()

        for tool in result.tools:
            tool_info = {
                "server": connection.name,
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema if hasattr(tool, "inputSchema") else {},
            }

            connection.tools[tool.name] = tool_info
            self._tools_cache[tool.name] = tool_info

            logger.debug(f"Discovered tool: {tool.name} from {connection.name}")

    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """Get tool definitions in OpenAI/Anthropic function calling format.

        Returns:
            List of tool definitions ready for LiteLLM
        """
        tools = []

        for tool_name, tool_info in self._tools_cache.items():
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": tool_info.get("description", ""),
                    "parameters": tool_info.get("input_schema", {"type": "object", "properties": {}}),
                },
            }
            tools.append(tool_def)

        return tools

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is available.

        Args:
            tool_name: Name of the tool

        Returns:
            True if the tool is available
        """
        return tool_name in self._tools_cache

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool on the appropriate MCP server.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result as a string

        Raises:
            ToolNotFoundError: If the tool is not found
        """
        if tool_name not in self._tools_cache:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found in any MCP server")

        tool_info = self._tools_cache[tool_name]
        server_name = tool_info["server"]
        connection = self._connections.get(server_name)

        if not connection or not connection.session:
            raise RuntimeError(f"Server '{server_name}' is not connected")

        logger.debug(f"Executing tool {tool_name} on server {server_name}")

        result = await connection.session.call_tool(tool_name, arguments)

        # Extract text content from result
        if result.content:
            # MCP returns content as a list of content blocks
            texts = []
            for content_block in result.content:
                if hasattr(content_block, "text"):
                    texts.append(content_block.text)
                elif hasattr(content_block, "data"):
                    # Handle binary/image data
                    texts.append(f"[Binary data: {content_block.mimeType}]")
            return "\n".join(texts)

        return ""

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        for connection in self._connections.values():
            await self._disconnect_server(connection)

        self._connections.clear()
        self._tools_cache.clear()

    async def _disconnect_server(self, connection: MCPServerConnection) -> None:
        """Disconnect from a single MCP server.

        Args:
            connection: Server connection object
        """
        # Close context managers in reverse order
        for cm in reversed(connection._context_managers):
            try:
                await cm.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error closing connection to {connection.name}: {e}")

        connection.session = None
        connection._context_managers.clear()

    async def __aenter__(self) -> "MCPManager":
        """Async context manager entry."""
        await self.connect_all()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect_all()

    # ==================== Synchronous API ====================
    # These methods manage a dedicated event loop for MCP operations,
    # allowing sync code to use async MCP connections without closing the loop.

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        """Ensure we have a running event loop for MCP operations.

        Creates a dedicated event loop running in a background thread
        that stays alive for the lifetime of the MCPManager.

        Returns:
            The event loop for MCP operations
        """
        if self._loop is None or self._loop.is_closed():
            import threading

            # Create a new event loop
            self._loop = asyncio.new_event_loop()

            # Run it in a background thread
            def run_loop(loop: asyncio.AbstractEventLoop) -> None:
                asyncio.set_event_loop(loop)
                loop.run_forever()

            self._loop_thread = threading.Thread(target=run_loop, args=(self._loop,), daemon=True)
            self._loop_thread.start()

        return self._loop

    def _run_async(self, coro: Any) -> Any:
        """Run an async coroutine in our dedicated event loop.

        Args:
            coro: The coroutine to run

        Returns:
            The result of the coroutine
        """
        import concurrent.futures

        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=120)  # 2 minute timeout

    def connect_all_sync(self) -> None:
        """Connect to all configured MCP servers (synchronous version).

        This creates a dedicated event loop that stays alive for tool execution.
        """
        if not MCP_AVAILABLE:
            raise MCPNotAvailableError(
                "MCP package not installed. Install with: pip install 'datascience-agent[mcp]'"
            )

        self._run_async(self.connect_all())

    def disconnect_all_sync(self) -> None:
        """Disconnect from all MCP servers and cleanup (synchronous version)."""
        if self._loop and not self._loop.is_closed():
            # Run disconnect in the event loop
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.disconnect_all(), self._loop
                )
                future.result(timeout=30)
            except Exception as e:
                logger.warning(f"Error during disconnect: {e}")

            # Stop the event loop
            self._loop.call_soon_threadsafe(self._loop.stop)

            # Wait for thread to finish
            if self._loop_thread and self._loop_thread.is_alive():
                self._loop_thread.join(timeout=5)

            # Close the loop
            try:
                self._loop.close()
            except Exception:
                pass

            self._loop = None
            self._loop_thread = None

    def execute_tool_sync(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool synchronously.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            Tool execution result as a string
        """
        return self._run_async(self.execute_tool(tool_name, arguments))
