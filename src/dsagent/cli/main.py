"""Main CLI entry point for DSAgent.

Provides subcommands:
- dsagent chat     : Interactive conversational mode (default)
- dsagent run      : One-shot task execution
- dsagent init     : Setup wizard
- dsagent mcp      : MCP server management
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from common locations
_env_locations = [
    Path.cwd() / ".env",
    Path(__file__).parent.parent.parent.parent / ".env",
    Path.home() / ".dsagent" / ".env",
]
for _env_path in _env_locations:
    if _env_path.exists():
        load_dotenv(_env_path)
        break


def cmd_chat(args: argparse.Namespace) -> int:
    """Run the interactive chat REPL."""
    from dsagent.cli.repl import run_chat
    return run_chat(args)


def cmd_run(args: argparse.Namespace) -> int:
    """Run a one-shot task."""
    from dsagent.cli.run import run_task
    return run_task(args)


def cmd_init(args: argparse.Namespace) -> int:
    """Run the setup wizard."""
    from dsagent.cli.init import run_init
    return run_init(args)


def cmd_mcp(args: argparse.Namespace) -> int:
    """Manage MCP servers."""
    from dsagent.cli.mcp_cmd import run_mcp
    return run_mcp(args)


def create_parser() -> argparse.ArgumentParser:
    """Create the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="dsagent",
        description="DSAgent - AI-powered Data Science Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  dsagent                          # Start interactive chat (default)
  dsagent chat                     # Same as above
  dsagent chat --model claude-sonnet-4-5
  dsagent run "Analyze sales.csv"  # One-shot task
  dsagent init                     # Setup wizard
  dsagent mcp add brave-search     # Add MCP server

For more info on a command:
  dsagent <command> --help
        """,
    )

    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show version and exit",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ========== chat subcommand ==========
    chat_parser = subparsers.add_parser(
        "chat",
        help="Interactive conversational mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  dsagent chat
  dsagent chat --model gpt-4o
  dsagent chat --session abc123
  dsagent chat --mcp-config ~/.dsagent/mcp.yaml
        """,
    )
    chat_parser.add_argument(
        "--model", "-m",
        type=str,
        default=os.getenv("LLM_MODEL", "gpt-4o"),
        help="LLM model to use (default: gpt-4o)",
    )
    chat_parser.add_argument(
        "--workspace", "-w",
        type=str,
        default="./workspace",
        help="Workspace directory (default: ./workspace)",
    )
    chat_parser.add_argument(
        "--session", "-s",
        type=str,
        default=None,
        help="Session ID to resume",
    )
    chat_parser.add_argument(
        "--hitl",
        type=str,
        choices=["none", "plan", "full", "plan_answer", "on_error"],
        default="none",
        help="Human-in-the-loop mode (default: none)",
    )
    chat_parser.add_argument(
        "--live-notebook",
        action="store_true",
        help="Enable live notebook (saves after each execution)",
    )
    chat_parser.add_argument(
        "--notebook-sync",
        action="store_true",
        help="Enable bidirectional notebook sync with Jupyter",
    )
    chat_parser.add_argument(
        "--mcp-config",
        type=str,
        default=None,
        help="Path to MCP servers YAML config file",
    )
    chat_parser.set_defaults(func=cmd_chat)

    # ========== run subcommand ==========
    run_parser = subparsers.add_parser(
        "run",
        help="Run a one-shot task",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  dsagent run "Analyze this dataset" --data ./data/sales.csv
  dsagent run "Build a predictive model" --data ./dataset
  dsagent run "Create visualizations" --workspace ./output
        """,
    )
    run_parser.add_argument(
        "task",
        type=str,
        help="The task to perform",
    )
    run_parser.add_argument(
        "--data", "-d",
        type=str,
        default=None,
        help="Path to data file or directory",
    )
    run_parser.add_argument(
        "--model", "-m",
        type=str,
        default=os.getenv("LLM_MODEL", "gpt-4o"),
        help="LLM model to use (default: gpt-4o)",
    )
    run_parser.add_argument(
        "--workspace", "-w",
        type=str,
        default="./workspace",
        help="Workspace directory (default: ./workspace)",
    )
    run_parser.add_argument(
        "--max-rounds", "-r",
        type=int,
        default=30,
        help="Maximum agent iterations (default: 30)",
    )
    run_parser.add_argument(
        "--hitl",
        type=str,
        choices=["none", "plan_only", "on_error", "plan_and_answer", "full"],
        default="none",
        help="Human-in-the-loop mode (default: none)",
    )
    run_parser.add_argument(
        "--mcp-config",
        type=str,
        default=None,
        help="Path to MCP servers YAML config file",
    )
    run_parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress verbose output",
    )
    run_parser.set_defaults(func=cmd_run)

    # ========== init subcommand ==========
    init_parser = subparsers.add_parser(
        "init",
        help="Setup wizard for DSAgent configuration",
        epilog="""
Interactively configure:
  - LLM provider and API keys
  - MCP tools (web search, etc.)
  - Default settings
        """,
    )
    init_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing configuration",
    )
    init_parser.set_defaults(func=cmd_init)

    # ========== mcp subcommand ==========
    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Manage MCP servers",
        epilog="""
Commands:
  dsagent mcp list              # List configured servers
  dsagent mcp add <template>    # Add from template
  dsagent mcp remove <name>     # Remove a server
        """,
    )
    mcp_subparsers = mcp_parser.add_subparsers(dest="mcp_command")

    # mcp list
    mcp_list = mcp_subparsers.add_parser("list", help="List configured MCP servers")
    mcp_list.set_defaults(mcp_action="list")

    # mcp add
    mcp_add = mcp_subparsers.add_parser("add", help="Add MCP server from template")
    mcp_add.add_argument("template", help="Template name (e.g., brave-search, filesystem)")
    mcp_add.set_defaults(mcp_action="add")

    # mcp remove
    mcp_remove = mcp_subparsers.add_parser("remove", help="Remove MCP server")
    mcp_remove.add_argument("name", help="Server name to remove")
    mcp_remove.set_defaults(mcp_action="remove")

    mcp_parser.set_defaults(func=cmd_mcp)

    return parser


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle --version
    if args.version:
        from dsagent import __version__
        print(f"dsagent {__version__}")
        return 0

    # Default to chat if no command specified
    if args.command is None:
        # Re-parse with 'chat' as default
        args = parser.parse_args(['chat'] + sys.argv[1:])

    # Run the command
    if hasattr(args, 'func'):
        try:
            return args.func(args)
        except KeyboardInterrupt:
            print("\nInterrupted")
            return 1
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
