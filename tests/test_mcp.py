"""Tests for MCP (Model Context Protocol) support."""

import pytest
from pathlib import Path
import tempfile
import yaml

from dsagent.tools.config import MCPServerConfig, MCPConfig


class TestMCPServerConfig:
    """Tests for MCPServerConfig model."""

    def test_create_stdio_config(self):
        """Test creating a stdio server config."""
        config = MCPServerConfig(
            name="test_server",
            transport="stdio",
            command=["python", "-m", "test_server"],
        )
        assert config.name == "test_server"
        assert config.transport == "stdio"
        assert config.command == ["python", "-m", "test_server"]
        assert config.enabled is True

    def test_create_http_config(self):
        """Test creating an HTTP server config."""
        config = MCPServerConfig(
            name="http_server",
            transport="http",
            url="http://localhost:8080/mcp",
        )
        assert config.name == "http_server"
        assert config.transport == "http"
        assert config.url == "http://localhost:8080/mcp"

    def test_resolve_env_variables(self):
        """Test environment variable resolution."""
        import os
        os.environ["TEST_API_KEY"] = "secret123"

        config = MCPServerConfig(
            name="test",
            command=["test"],
            env={"API_KEY": "${TEST_API_KEY}", "STATIC": "value"},
        )

        resolved = config.resolve_env()
        assert resolved["API_KEY"] == "secret123"
        assert resolved["STATIC"] == "value"

        del os.environ["TEST_API_KEY"]

    def test_disabled_server(self):
        """Test disabled server config."""
        config = MCPServerConfig(
            name="disabled",
            command=["test"],
            enabled=False,
        )
        assert config.enabled is False


class TestMCPConfig:
    """Tests for MCPConfig model."""

    def test_from_dict(self):
        """Test creating config from dictionary."""
        config = MCPConfig.from_dict({
            "web_search": {
                "command": ["npx", "mcp-server"],
                "env": {"API_KEY": "test"},
            },
            "filesystem": {
                "command": ["python", "-m", "fs_server"],
            },
        })

        assert len(config.servers) == 2
        assert config.servers[0].name == "web_search"
        assert config.servers[1].name == "filesystem"

    def test_from_yaml(self):
        """Test loading config from YAML file."""
        yaml_content = """
servers:
  - name: test_server
    transport: stdio
    command: ["python", "-m", "test"]
    enabled: true
  - name: http_server
    transport: http
    url: http://localhost:8080/mcp
    enabled: false
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            config = MCPConfig.from_yaml(f.name)

            assert len(config.servers) == 2
            assert config.servers[0].name == "test_server"
            assert config.servers[1].name == "http_server"
            assert config.servers[1].enabled is False

            Path(f.name).unlink()

    def test_get_enabled_servers(self):
        """Test filtering enabled servers."""
        config = MCPConfig(servers=[
            MCPServerConfig(name="enabled1", command=["test"], enabled=True),
            MCPServerConfig(name="disabled", command=["test"], enabled=False),
            MCPServerConfig(name="enabled2", command=["test"], enabled=True),
        ])

        enabled = config.get_enabled_servers()
        assert len(enabled) == 2
        assert enabled[0].name == "enabled1"
        assert enabled[1].name == "enabled2"

    def test_empty_config(self):
        """Test empty config."""
        config = MCPConfig()
        assert len(config.servers) == 0
        assert config.get_enabled_servers() == []


class TestMCPManager:
    """Tests for MCPManager class."""

    def test_manager_creation(self):
        """Test creating MCPManager."""
        from dsagent.tools.mcp_manager import MCPManager

        manager = MCPManager()
        assert manager.is_available  # MCP package should be installed
        assert len(manager.connected_servers) == 0
        assert len(manager.available_tools) == 0

    def test_manager_from_dict(self):
        """Test creating manager from dictionary."""
        from dsagent.tools.mcp_manager import MCPManager

        manager = MCPManager.from_dict({
            "test": {
                "command": ["python", "-m", "test"],
                "enabled": False,  # Disabled so we don't try to connect
            }
        })

        assert len(manager.config.servers) == 1
        assert manager.config.servers[0].name == "test"

    def test_get_tools_empty(self):
        """Test getting tools when no servers connected."""
        from dsagent.tools.mcp_manager import MCPManager

        manager = MCPManager()
        tools = manager.get_tools_for_llm()
        assert tools == []

    def test_has_tool_false(self):
        """Test has_tool returns False when tool not found."""
        from dsagent.tools.mcp_manager import MCPManager

        manager = MCPManager()
        assert manager.has_tool("nonexistent") is False
