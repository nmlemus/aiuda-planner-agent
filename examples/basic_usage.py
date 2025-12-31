#!/usr/bin/env python3
"""Basic usage example for the Aiuda Planner Agent.

This example demonstrates:
1. Creating a simple dataset
2. Running the agent to analyze it
3. Getting the results and generated notebook
"""

import os
from pathlib import Path

# Ensure we have an API key
if not os.getenv("OPENAI_API_KEY"):
    print("Please set OPENAI_API_KEY environment variable")
    print("export OPENAI_API_KEY=sk-your-key-here")
    exit(1)

from datapilot import PlannerAgent


def main():
    # Create a workspace directory
    workspace = Path("./workspace")
    workspace.mkdir(exist_ok=True)

    # Create a sample dataset
    sample_data = """date,product,region,sales,units
2024-01-01,Widget A,North,1200,45
2024-01-01,Widget A,South,980,38
2024-01-01,Widget B,North,2100,62
2024-01-01,Widget B,South,1850,55
2024-01-02,Widget A,North,1350,52
2024-01-02,Widget A,South,1100,42
2024-01-02,Widget B,North,2250,68
2024-01-02,Widget B,South,1920,58
2024-01-03,Widget A,North,1180,44
2024-01-03,Widget A,South,890,35
2024-01-03,Widget B,North,2050,60
2024-01-03,Widget B,South,1780,53
"""
    (workspace / "sales_data.csv").write_text(sample_data)
    print(f"Created sample data at: {workspace / 'sales_data.csv'}")

    # Create and run the agent
    print("\n" + "=" * 60)
    print("Starting Aiuda Planner Agent")
    print("=" * 60)

    with PlannerAgent(
        model="gpt-4o",
        workspace=workspace,
        verbose=True,
    ) as agent:
        result = agent.run(
            "Analyze the sales_data.csv file. "
            "Calculate total sales by product and region. "
            "Create a visualization showing the comparison. "
            "Identify the best performing product-region combination."
        )

    # Print results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"\nAnswer:\n{result.answer}")
    print(f"\nNotebook saved to: {result.notebook_path}")
    print(f"Rounds used: {result.rounds}")


if __name__ == "__main__":
    main()
