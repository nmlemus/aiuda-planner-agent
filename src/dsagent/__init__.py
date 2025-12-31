"""AI Planner Agent - A planning-based data analysis agent.

This package provides a powerful agent for data analysis tasks that:
- Creates and follows dynamic plans
- Executes Python code in a persistent Jupyter kernel
- Supports multiple LLM providers via LiteLLM
- Generates clean Jupyter notebooks
- Streams events for real-time UI updates

Basic usage:
    from dsagent import PlannerAgent

    with PlannerAgent(model="gpt-4o") as agent:
        result = agent.run("Analyze sales data and find trends")
        print(result.answer)

With streaming:
    from dsagent import PlannerAgent, EventType

    agent = PlannerAgent()
    for event in agent.run_stream("Build a model"):
        if event.type == EventType.CODE_COMPLETED:
            print(f"Code: {event.success}")
"""

from dsagent.agents.base import PlannerAgent, AgentResult
from dsagent.schema.models import (
    AgentConfig,
    AgentEvent,
    EventType,
    ExecutionResult,
    PlanState,
    PlanStep,
    SessionState,
)
from dsagent.core.executor import JupyterExecutor
from dsagent.core.engine import AgentEngine
from dsagent.core.planner import PlanParser
from dsagent.core.context import RunContext
from dsagent.utils.logger import AgentLogger, Colors
from dsagent.utils.notebook import NotebookBuilder, ExecutionTracker
from dsagent.utils.run_logger import RunLogger

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
