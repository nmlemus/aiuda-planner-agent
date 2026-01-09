"""MCP server management CLI for DSAgent.

This module provides the `dsagent mcp` command for managing
MCP server configurations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

# MCP server templates
# Using official @modelcontextprotocol packages (the MCP standard)
MCP_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "brave-search": {
        "name": "brave_search",
        "description": "Web search via Brave Search API",
        "transport": "stdio",
        "command": ["npx", "-y", "@modelcontextprotocol/server-brave-search"],
        "env": {"BRAVE_API_KEY": "${BRAVE_API_KEY}"},
        "required_env": ["BRAVE_API_KEY"],
    },
    "filesystem": {
        "name": "filesystem",
        "description": "Local file system access",
        "transport": "stdio",
        "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem"],
        "args_prompt": "Enter paths to allow access (comma-separated)",
    },
    "github": {
        "name": "github",
        "description": "GitHub repository access",
        "transport": "stdio",
        "command": ["npx", "-y", "@modelcontextprotocol/server-github"],
        "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"},
        "required_env": ["GITHUB_TOKEN"],
    },
    "memory": {
        "name": "memory",
        "description": "Persistent memory/knowledge base",
        "transport": "stdio",
        "command": ["npx", "-y", "@modelcontextprotocol/server-memory"],
    },
    "fetch": {
        "name": "fetch",
        "description": "Fetch and parse web content",
        "transport": "stdio",
        "command": ["npx", "-y", "@modelcontextprotocol/server-fetch"],
    },
    "bigquery": {
        "name": "bigquery",
        "description": "Google BigQuery database access (requires Google Toolbox)",
        "transport": "stdio",
        "command_prompt": "Enter path to Google Toolbox binary",
        "command_template": ["{toolbox_path}", "--prebuilt", "bigquery", "--stdio"],
        "env": {"BIGQUERY_PROJECT": "${BIGQUERY_PROJECT}"},
        "required_env": ["BIGQUERY_PROJECT"],
    },
}


def get_mcp_config_path() -> Path:
    """Get the default MCP config file path."""
    return Path.home() / ".dsagent" / "mcp.yaml"


def load_mcp_config(path: Path) -> Dict[str, Any]:
    """Load MCP config from YAML file."""
    if not path.exists():
        return {"servers": []}

    import yaml
    with open(path) as f:
        return yaml.safe_load(f) or {"servers": []}


def save_mcp_config(path: Path, config: Dict[str, Any]) -> None:
    """Save MCP config to YAML file."""
    import yaml
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def cmd_list(console: Console, config_path: Path) -> int:
    """List configured MCP servers."""
    config = load_mcp_config(config_path)
    servers = config.get("servers", [])

    if not servers:
        console.print("[yellow]No MCP servers configured.[/yellow]")
        console.print(f"\nRun [cyan]dsagent mcp add <template>[/cyan] to add a server.")
        console.print("\nAvailable templates:")
        for name, template in MCP_TEMPLATES.items():
            console.print(f"  [cyan]{name}[/cyan] - {template['description']}")
        return 0

    table = Table(title="Configured MCP Servers")
    table.add_column("Name", style="cyan")
    table.add_column("Transport", style="green")
    table.add_column("Command")

    for server in servers:
        name = server.get("name", "unknown")
        transport = server.get("transport", "stdio")
        command = " ".join(server.get("command", []))
        table.add_row(name, transport, command[:50] + "..." if len(command) > 50 else command)

    console.print(table)
    console.print(f"\nConfig file: [dim]{config_path}[/dim]")
    return 0


def cmd_add(console: Console, config_path: Path, template_name: str) -> int:
    """Add MCP server from template."""
    if template_name not in MCP_TEMPLATES:
        console.print(f"[red]Unknown template: {template_name}[/red]")
        console.print("\nAvailable templates:")
        for name, template in MCP_TEMPLATES.items():
            console.print(f"  [cyan]{name}[/cyan] - {template['description']}")
        return 1

    template = MCP_TEMPLATES[template_name]
    console.print(f"\n[bold]Adding {template_name}[/bold]: {template['description']}")

    # Build server config
    server_config: Dict[str, Any] = {
        "name": template["name"],
        "transport": template["transport"],
    }

    # Handle command - either direct or template-based
    if "command" in template:
        server_config["command"] = list(template["command"])
    elif "command_template" in template:
        # Prompt for values needed in the template
        if "command_prompt" in template:
            value = Prompt.ask(template["command_prompt"])
            # Replace placeholder in command template
            server_config["command"] = [
                part.format(toolbox_path=value) if "{" in part else part
                for part in template["command_template"]
            ]
        else:
            server_config["command"] = list(template["command_template"])

    # Handle command arguments (for filesystem, etc.)
    if "args_prompt" in template:
        args = Prompt.ask(template["args_prompt"])
        server_config["command"].extend(args.split(","))

    # Handle environment variables
    if "env" in template:
        server_config["env"] = dict(template["env"])

    # Check for required environment variables
    env_file = Path.home() / ".dsagent" / ".env"
    if "required_env" in template:
        console.print("\n[bold]Required environment variables:[/bold]")
        env_updates = []
        for var in template["required_env"]:
            import os
            if not os.environ.get(var):
                value = Prompt.ask(f"Enter {var}", password=True)
                env_updates.append(f"{var}={value}")
                console.print(f"  [green]+ {var}[/green]")
            else:
                console.print(f"  [dim]{var} (already set)[/dim]")

        # Append to .env file
        if env_updates:
            env_file.parent.mkdir(parents=True, exist_ok=True)
            with open(env_file, "a") as f:
                for line in env_updates:
                    f.write(line + "\n")
            console.print(f"\nUpdated {env_file}")

    # Load existing config and add server
    config = load_mcp_config(config_path)
    servers = config.get("servers", [])

    # Check if server already exists
    existing_names = {s.get("name") for s in servers}
    if server_config["name"] in existing_names:
        console.print(f"[yellow]Server '{server_config['name']}' already configured.[/yellow]")
        return 1

    servers.append(server_config)
    config["servers"] = servers
    save_mcp_config(config_path, config)

    console.print(f"\n[green]Added {template_name} to {config_path}[/green]")
    console.print(f"\nUse with: [cyan]dsagent chat --mcp-config {config_path}[/cyan]")
    return 0


def cmd_remove(console: Console, config_path: Path, server_name: str) -> int:
    """Remove MCP server by name."""
    config = load_mcp_config(config_path)
    servers = config.get("servers", [])

    # Find and remove server
    new_servers = [s for s in servers if s.get("name") != server_name]

    if len(new_servers) == len(servers):
        console.print(f"[red]Server '{server_name}' not found.[/red]")
        return 1

    config["servers"] = new_servers
    save_mcp_config(config_path, config)

    console.print(f"[green]Removed '{server_name}' from {config_path}[/green]")
    return 0


def run_mcp(args) -> int:
    """Run MCP management command.

    Args:
        args: Namespace with mcp_command and related args

    Returns:
        Exit code (0 for success)
    """
    console = Console()
    config_path = get_mcp_config_path()

    mcp_action = getattr(args, "mcp_action", None)

    if mcp_action == "list":
        return cmd_list(console, config_path)

    elif mcp_action == "add":
        return cmd_add(console, config_path, args.template)

    elif mcp_action == "remove":
        return cmd_remove(console, config_path, args.name)

    else:
        # No subcommand, show help
        console.print("[bold]MCP Server Management[/bold]")
        console.print()
        console.print("Commands:")
        console.print("  [cyan]dsagent mcp list[/cyan]              List configured servers")
        console.print("  [cyan]dsagent mcp add <template>[/cyan]    Add server from template")
        console.print("  [cyan]dsagent mcp remove <name>[/cyan]     Remove a server")
        console.print()
        console.print("Available templates:")
        for name, template in MCP_TEMPLATES.items():
            console.print(f"  [cyan]{name}[/cyan] - {template['description']}")
        return 0
