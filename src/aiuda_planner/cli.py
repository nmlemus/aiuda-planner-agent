#!/usr/bin/env python3
"""Command-line interface for the Aiuda Planner Agent."""

import argparse
import os
import sys
import shutil
from pathlib import Path

# Load .env file if exists (before importing agent)
from dotenv import load_dotenv
load_dotenv()  # Loads from .env in current directory
load_dotenv(Path.home() / ".aiuda" / ".env")  # Also check ~/.aiuda/.env

from aiuda_planner import PlannerAgent, EventType


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="AI Planner Agent - Analyze data with dynamic planning",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  aiuda-planner "Analyze sales data" --data ./data/sales.csv
  aiuda-planner "Build a predictive model" --data ./dataset --model gpt-4o
  aiuda-planner "Create visualizations" --data ./data --workspace ./output
        """,
    )

    parser.add_argument(
        "task",
        type=str,
        help="The task to perform (e.g., 'Analyze this dataset and find trends')",
    )

    parser.add_argument(
        "--data", "-d",
        type=str,
        required=True,
        help="Path to data file or directory to analyze",
    )

    parser.add_argument(
        "--model", "-m",
        type=str,
        default=os.getenv("LLM_MODEL", "gpt-4o"),
        help="LLM model to use (default: gpt-4o)",
    )

    parser.add_argument(
        "--workspace", "-w",
        type=str,
        default="./workspace",
        help="Workspace directory for outputs (default: ./workspace)",
    )

    parser.add_argument(
        "--max-rounds", "-r",
        type=int,
        default=30,
        help="Maximum agent iterations (default: 30)",
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress verbose output",
    )

    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable streaming output",
    )

    args = parser.parse_args()

    # Validate data path
    data_path = Path(args.data).resolve()
    if not data_path.exists():
        print(f"Error: Data path does not exist: {data_path}", file=sys.stderr)
        sys.exit(1)

    # Setup workspace
    workspace = Path(args.workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    # Copy data to workspace
    data_dest = workspace / "data"
    data_dest.mkdir(exist_ok=True)

    if data_path.is_file():
        dest_file = data_dest / data_path.name
        shutil.copy2(data_path, dest_file)
        data_info = f"File '{data_path.name}' copied to workspace"
    else:
        # Copy directory contents
        for item in data_path.iterdir():
            if item.is_file():
                shutil.copy2(item, data_dest / item.name)
        data_info = f"Directory contents from '{data_path.name}' copied to workspace"

    print(f"Data: {data_info}")
    print(f"Workspace: {workspace}")
    print(f"Model: {args.model}")
    print("-" * 60)

    # Build task with data context
    task_with_context = f"""
{args.task}

The data is available in the 'data/' subdirectory of the current working directory.
List files in 'data/' first to see what's available.
"""

    # Create and run agent
    agent = PlannerAgent(
        model=args.model,
        workspace=workspace,
        max_rounds=args.max_rounds,
        verbose=not args.quiet,
    )

    try:
        agent.start()

        if args.no_stream:
            # Synchronous mode
            result = agent.run(task_with_context)
            print("\n" + "=" * 60)
            print("RESULT")
            print("=" * 60)
            print(result.answer)
        else:
            # Streaming mode
            for event in agent.run_stream(task_with_context):
                if args.quiet:
                    # In quiet mode, only show key events
                    if event.type == EventType.ROUND_STARTED:
                        print(f"Round {event.message}")
                    elif event.type == EventType.CODE_SUCCESS:
                        print("  [OK] Code executed")
                    elif event.type == EventType.CODE_FAILED:
                        print("  [FAIL] Code failed")
                    elif event.type == EventType.ANSWER_ACCEPTED:
                        print(f"\nAnswer:\n{event.message}")

            # Get final result with notebook
            result = agent.get_result()

        print("\n" + "=" * 60)
        print(f"Notebook: {result.notebook_path}")
        print(f"Rounds: {result.rounds}")
        print(f"Images: {workspace / 'images'}")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        agent.shutdown()


if __name__ == "__main__":
    main()
