"""AI Planner Agent - A planning-based data analysis agent.

This package provides a powerful agent for data analysis tasks that:
- Creates and follows dynamic plans
- Executes Python code in a persistent Jupyter kernel
- Supports multiple LLM providers via LiteLLM
- Generates clean Jupyter notebooks
- Streams events for real-time UI updates

Basic usage:
    from aiuda_planner import PlannerAgent

    with PlannerAgent(model="gpt-4o") as agent:
        result = agent.run("Analyze sales data and find trends")
        print(result.answer)

With streaming:
    from aiuda_planner import PlannerAgent, EventType

    agent = PlannerAgent()
    for event in agent.run_stream("Build a model"):
        if event.type == EventType.CODE_COMPLETED:
            print(f"Code: {event.success}")
"""

from aiuda_planner.agents.base import PlannerAgent, AgentResult
from aiuda_planner.schema.models import (
    AgentConfig,
    AgentEvent,
    EventType,
    ExecutionResult,
    PlanState,
    PlanStep,
    SessionState,
)
from aiuda_planner.core.executor import JupyterExecutor
from aiuda_planner.core.engine import AgentEngine
from aiuda_planner.core.planner import PlanParser
from aiuda_planner.core.context import RunContext
from aiuda_planner.utils.logger import AgentLogger, Colors
from aiuda_planner.utils.notebook import NotebookBuilder, ExecutionTracker
from aiuda_planner.utils.run_logger import RunLogger

__version__ = "0.3.0"

__all__ = [
    # Main classes
    "PlannerAgent",
    "AgentResult",
    # Configuration
    "AgentConfig",
    # Events
    "AgentEvent",
    "EventType",
    # Execution
    "ExecutionResult",
    "JupyterExecutor",
    # Planning
    "PlanState",
    "PlanStep",
    "PlanParser",
    # Engine
    "AgentEngine",
    # Session
    "SessionState",
    # Context and Logging
    "RunContext",
    "RunLogger",
    # Utilities
    "AgentLogger",
    "Colors",
    "NotebookBuilder",
    "ExecutionTracker",
]
