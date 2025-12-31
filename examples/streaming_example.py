#!/usr/bin/env python3
"""Streaming example for the Aiuda Planner Agent.

This example demonstrates:
1. Using the streaming API
2. Handling different event types
3. Real-time progress updates
"""

import os
from pathlib import Path

# Ensure we have an API key
if not os.getenv("OPENAI_API_KEY"):
    print("Please set OPENAI_API_KEY environment variable")
    exit(1)

from dsagent import PlannerAgent, EventType


def main():
    workspace = Path("./workspace")
    workspace.mkdir(exist_ok=True)

    # Create sample data
    sample_data = """name,age,salary,department,years_experience
Alice,32,75000,Engineering,5
Bob,45,95000,Engineering,15
Carol,28,62000,Marketing,3
David,38,82000,Engineering,10
Eve,41,88000,Sales,12
Frank,29,58000,Marketing,2
Grace,35,78000,Sales,8
Henry,52,110000,Engineering,22
Ivy,26,55000,Marketing,1
Jack,44,92000,Sales,14
"""
    (workspace / "employees.csv").write_text(sample_data)

    # Create agent
    agent = PlannerAgent(
        model="gpt-4o",
        workspace=workspace,
        verbose=False,  # We'll handle output ourselves
    )
    agent.start()

    print("\nStarting analysis with streaming events...\n")
    print("-" * 50)

    try:
        for event in agent.run_stream(
            "Analyze employees.csv. Calculate average salary by department. "
            "Find correlation between years_experience and salary. "
            "Create visualizations."
        ):
            # Handle different event types
            if event.type == EventType.AGENT_STARTED:
                print(f"[STARTED] {event.message}")

            elif event.type == EventType.ROUND_STARTED:
                print(f"\n[ROUND] {event.message}")

            elif event.type == EventType.PLAN_UPDATED:
                print(f"[PLAN] Updated plan:")
                plan_text = event.plan.raw_text if event.plan else ""
                for line in plan_text.split("\n")[:5]:
                    print(f"  {line}")

            elif event.type == EventType.CODE_EXECUTING:
                print(f"[CODE] Executing code...")

            elif event.type == EventType.CODE_SUCCESS:
                print(f"[CODE] Success")

            elif event.type == EventType.CODE_FAILED:
                print(f"[CODE] Failed")

            elif event.type == EventType.ANSWER_ACCEPTED:
                print(f"\n[ANSWER]\n{event.message}")

            elif event.type == EventType.AGENT_ERROR:
                print(f"[ERROR] {event.message}")

            elif event.type == EventType.AGENT_FINISHED:
                print(f"\n[COMPLETED]")

        # After streaming, get the final result with notebook
        result = agent.get_result()
        print(f"\nNotebook saved to: {result.notebook_path}")
        print(f"Rounds used: {result.rounds}")

    finally:
        agent.shutdown()

    print("-" * 50)
    print("Done!")


if __name__ == "__main__":
    main()
