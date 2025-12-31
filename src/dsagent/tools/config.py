"""Configuration models for MCP servers and tools."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union

import yaml
from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""

    # Server identification
    name: str = Field(..., description="Unique name for this server")

    # Transport type
    transport: Literal["stdio", "http"] = Field(
        default="stdio",
        description="Transport type: 'stdio' for local process, 'http' for remote server",
    )

    # Stdio transport options
    command: Optional[List[str]] = Field(
        default=None,
        description="Command to start the MCP server (for stdio transport)",
    )
    env: Optional[Dict[str, str]] = Field(
        default=None,
        description="Environment variables for the server process",
    )

    # HTTP transport options
    url: Optional[str] = Field(
        default=None,
        description="URL of the MCP server (for http transport)",
    )

    # Common options
    enabled: bool = Field(default=True, description="Whether this server is enabled")
    cache_tools: bool = Field(
        default=True,
        description="Cache tool definitions to reduce latency",
    )

    def resolve_env(self) -> Dict[str, str]:
        """Resolve environment variables (expand ${VAR} references)."""
        if not self.env:
            return {}

        resolved = {}
        for key, value in self.env.items():
            if value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                resolved[key] = os.environ.get(env_var, "")
            else:
                resolved[key] = value
        return resolved


class MCPConfig(BaseModel):
    """Configuration for all MCP servers."""

    servers: List[MCPServerConfig] = Field(
        default_factory=list,
        description="List of MCP server configurations",
    )

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "MCPConfig":
        """Load MCP configuration from a YAML file.

        Args:
            path: Path to the YAML configuration file

        Returns:
            MCPConfig instance

        Example YAML:
            servers:
              - name: web_search
                transport: stdio
                command: ["npx", "-y", "@anthropic/mcp-server-brave-search"]
                env:
                  BRAVE_API_KEY: "${BRAVE_API_KEY}"

              - name: filesystem
                transport: stdio
                command: ["npx", "-y", "@anthropic/mcp-server-filesystem", "/data"]

              - name: custom_api
                transport: http
                url: "http://localhost:8080/mcp"
        """
        path = Path(path).expanduser().resolve()

        if not path.exists():
            raise FileNotFoundError(f"MCP config file not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        # Handle both formats: list of servers or dict with 'servers' key
        if isinstance(data, list):
            servers = data
        elif isinstance(data, dict):
            servers = data.get("servers", [])
        else:
            servers = []

        # Convert dict servers to MCPServerConfig
        server_configs = []
        for server in servers:
            if isinstance(server, dict):
                # If server is a dict without 'name', use the key as name
                if "name" not in server and len(servers) == 1:
                    server["name"] = "default"
                server_configs.append(MCPServerConfig(**server))
            elif isinstance(server, MCPServerConfig):
                server_configs.append(server)

        return cls(servers=server_configs)

    @classmethod
    def from_dict(cls, data: Dict) -> "MCPConfig":
        """Create MCPConfig from a dictionary.

        Args:
            data: Dictionary with server configurations

        Returns:
            MCPConfig instance
        """
        servers = []
        for name, config in data.items():
            if isinstance(config, dict):
                config["name"] = name
                servers.append(MCPServerConfig(**config))
        return cls(servers=servers)

    def get_enabled_servers(self) -> List[MCPServerConfig]:
        """Get list of enabled server configurations."""
        return [s for s in self.servers if s.enabled]
