"""Main PlannerAgent class - the primary interface for users."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Callable, Any, Generator, TYPE_CHECKING
from datetime import datetime

from dsagent.schema.models import (
    AgentConfig,
    AgentEvent,
    EventType,
    SessionState,
    PlanState,
)
from dsagent.core.executor import JupyterExecutor
from dsagent.core.engine import AgentEngine
from dsagent.utils.logger import AgentLogger
from dsagent.utils.notebook import NotebookBuilder

if TYPE_CHECKING:
    from dsagent.core.context import RunContext
    from dsagent.utils.run_logger import RunLogger


class PlannerAgent:
    """High-level planner agent for data analysis tasks.

    This is the main class users interact with. It orchestrates:
    - Jupyter kernel for code execution
    - LLM communication via LiteLLM
    - Plan tracking and management
    - Notebook generation
    - Event streaming for UI integration

    Example - Basic usage:
        agent = PlannerAgent(
            model="gpt-4o",
            workspace="./workspace",
        )
        result = agent.run("Analyze sales_data.csv and find trends")
        print(result.answer)
        print(f"Notebook saved to: {result.notebook_path}")

    Example - With streaming:
        agent = PlannerAgent(model="claude-3-sonnet-20240229")

        for event in agent.run_stream("Build a predictive model"):
            if event.type == EventType.CODE_COMPLETED:
                print(f"Code executed: {event.success}")
            elif event.type == EventType.ANSWER:
                print(f"Answer: {event.message}")

    Example - FastAPI integration:
        @app.post("/analyze")
        async def analyze(task: str):
            agent = PlannerAgent(
                session_id=str(uuid4()),
                event_callback=send_sse_event,
            )
            return agent.run(task)
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        workspace: str | Path = "./workspace",
        session_id: Optional[str] = None,
        max_rounds: int = 30,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        timeout: int = 300,
        verbose: bool = True,
        event_callback: Optional[Callable[[AgentEvent], Any]] = None,
        context: Optional["RunContext"] = None,
    ) -> None:
        """Initialize the planner agent.

        Args:
            model: LLM model to use (any LiteLLM-supported model)
            workspace: Working directory for files and notebooks
            session_id: Unique session identifier (for multi-user scenarios)
            max_rounds: Maximum agent loop iterations
            max_tokens: Max tokens per LLM response
            temperature: LLM temperature (0.0-1.0)
            timeout: Code execution timeout in seconds
            verbose: Print to console
            event_callback: Callback for streaming events to UI
            context: RunContext for organized workspace structure
        """
        # Store or create context
        self.context = context
        if context:
            self.workspace = context.run_path
        else:
            self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

        # Create configuration
        self.config = AgentConfig(
            model=model,
            session_id=session_id,
            max_rounds=max_rounds,
            max_tokens=max_tokens,
            temperature=temperature,
            workspace=str(self.workspace),
        )

        # Initialize run logger if context provided
        self._run_logger: Optional["RunLogger"] = None
        if context:
            from dsagent.utils.run_logger import RunLogger
            self._run_logger = RunLogger(context)

        # Initialize components
        self.executor = JupyterExecutor(
            workspace=self.workspace,
            timeout=timeout,
        )

        self.logger = AgentLogger(
            verbose=verbose,
            event_callback=event_callback,
        )

        self.event_callback = event_callback
        self._engine: Optional[AgentEngine] = None
        self._notebook: Optional[NotebookBuilder] = None
        self._started = False

    def start(self) -> None:
        """Start the agent (initializes Jupyter kernel).

        Call this before running tasks, or use the context manager.
        """
        if self._started:
            return

        self.executor.start()
        self._started = True
        self.logger.info("PlannerAgent started")

    def shutdown(self) -> None:
        """Shutdown the agent (stops Jupyter kernel)."""
        if not self._started:
            return

        # Close run logger if present
        if self._run_logger:
            self._run_logger.close()

        self.executor.shutdown()
        self._started = False
        self.logger.info("PlannerAgent stopped")

    def __enter__(self) -> "PlannerAgent":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.shutdown()

    def run(self, task: str) -> "AgentResult":
        """Run the agent on a task synchronously.

        Args:
            task: The user's task description

        Returns:
            AgentResult with answer, notebook path, etc.
        """
        # Consume the generator
        events = list(self.run_stream(task))
        return self._build_result(events)

    def run_stream(self, task: str) -> Generator[AgentEvent, None, None]:
        """Run the agent with streaming events.

        Args:
            task: The user's task description

        Yields:
            AgentEvent for each significant event
        """
        # Auto-start if needed
        if not self._started:
            self.start()

        # Initialize notebook builder with context if available
        self._notebook = NotebookBuilder(
            task=task,
            workspace=self.workspace,
            context=self.context,
        )

        # Create engine with run logger if available
        self._engine = AgentEngine(
            config=self.config,
            executor=self.executor,
            logger=self.logger,
            notebook_builder=self._notebook,
            event_callback=self.event_callback,
            run_logger=self._run_logger,
        )

        # Run the agent loop
        self.logger.print_header(f"Task: {task}")

        yield from self._engine.run_stream(task)

        # Generate clean notebook at the end
        self.logger.print_header("Task Complete")

    def get_result(self) -> "AgentResult":
        """Get the result after streaming completes.

        Call this after consuming all events from run_stream() to get
        the final result including the generated notebook.

        Returns:
            AgentResult with answer, notebook path, etc.
        """
        if not self._engine:
            raise RuntimeError("No run in progress. Call run_stream() first.")

        answer = self._engine.answer
        notebook_path = None

        # Generate and save clean notebook
        if self._notebook:
            clean_notebook = self._notebook.generate_clean_notebook(
                final_plan=self._engine.current_plan,
                answer=answer,
            )
            notebook_path = clean_notebook.save()

        return AgentResult(
            answer=answer or "No answer generated",
            notebook_path=notebook_path,
            events=[],  # Events were already consumed
            plan=self._engine.current_plan,
            rounds=self._engine.round_num,
        )

    def _build_result(self, events: list[AgentEvent]) -> "AgentResult":
        """Build result object from events.

        Args:
            events: List of all events from the run

        Returns:
            AgentResult object
        """
        answer = None
        notebook_path = None

        # Find answer event
        for event in events:
            if event.type == EventType.ANSWER_ACCEPTED:
                answer = event.message
                break

        # Generate and save clean notebook
        if self._engine and self._notebook:
            clean_notebook = self._notebook.generate_clean_notebook(
                final_plan=self._engine.current_plan,
                answer=answer,
            )
            notebook_path = clean_notebook.save()

        return AgentResult(
            answer=answer or "No answer generated",
            notebook_path=notebook_path,
            events=events,
            plan=self._engine.current_plan if self._engine else None,
            rounds=self._engine.round_num if self._engine else 0,
        )

    def serialize_state(self) -> str:
        """Serialize agent state for persistence.

        Returns:
            JSON string of agent state
        """
        state = SessionState(
            session_id=self.config.session_id or "default",
            config=self.config,
            messages=self._engine.messages if self._engine else [],
            round_num=self._engine.round_num if self._engine else 0,
            current_plan=self._engine.current_plan if self._engine else None,
        )
        return state.model_dump_json(indent=2)

    def restore_state(self, state_json: str) -> None:
        """Restore agent state from persistence.

        Args:
            state_json: JSON string of agent state
        """
        state = SessionState.model_validate_json(state_json)
        self.config = state.config

        if self._engine:
            self._engine.messages = state.messages
            self._engine.round_num = state.round_num
            self._engine.current_plan = state.current_plan


class AgentResult:
    """Result from running the planner agent.

    Attributes:
        answer: The final answer text
        notebook_path: Path to generated Jupyter notebook
        events: All events from the run
        plan: Final plan state
        rounds: Number of rounds executed
    """

    def __init__(
        self,
        answer: str,
        notebook_path: Optional[Path],
        events: list[AgentEvent],
        plan: Optional[PlanState],
        rounds: int,
    ) -> None:
        """Initialize the result.

        Args:
            answer: Final answer text
            notebook_path: Path to notebook
            events: All events
            plan: Final plan state
            rounds: Number of rounds
        """
        self.answer = answer
        self.notebook_path = notebook_path
        self.events = events
        self.plan = plan
        self.rounds = rounds

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"AgentResult(answer={self.answer[:50]}..., "
            f"notebook={self.notebook_path}, rounds={self.rounds})"
        )

    @property
    def success(self) -> bool:
        """Check if the run was successful."""
        return self.answer and "error" not in self.answer.lower()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "answer": self.answer,
            "notebook_path": str(self.notebook_path) if self.notebook_path else None,
            "rounds": self.rounds,
            "plan": self.plan.raw_text if self.plan else None,
            "success": self.success,
        }
