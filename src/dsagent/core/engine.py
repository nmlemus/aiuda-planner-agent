"""Main agent engine for orchestrating the planning loop."""

from __future__ import annotations

import re
from typing import Optional, Callable, Any, Generator, TYPE_CHECKING

from litellm import completion

from dsagent.schema.models import (
    AgentConfig,
    ExecutionResult,
    EventType,
    AgentEvent,
    PlanState,
)
from dsagent.core.planner import PlanParser
from dsagent.core.executor import JupyterExecutor
from dsagent.utils.notebook import NotebookBuilder
from dsagent.utils.logger import AgentLogger, Colors

if TYPE_CHECKING:
    from dsagent.schema.models import Message
    from dsagent.utils.run_logger import RunLogger


# System prompt for the planner agent
SYSTEM_PROMPT = '''You are an autonomous AI agent that works with a STRUCTURED PLAN to complete data analysis and machine learning tasks.

## How You Work

1. **FIRST**: Create a DETAILED plan with numbered steps (8-12 steps for complex tasks)
2. **THEN**: Execute each step one by one
3. **TRACK**: Mark steps as complete [x] or pending [ ]
4. **ADAPT**: Adjust the plan if needed based on results
5. **FINISH**: Only provide final answer when ALL steps are complete

## Response Format

EVERY response must include these XML tags:

### <plan> - Your current plan status (REQUIRED in every response)
```
<plan>
1. [x] Completed step
2. [ ] Current step          <- Working on this
3. [ ] Future step
</plan>
```

### <think> - Your reasoning (not executed)
Analyze results, explain decisions, plan next actions.

### <plan_update> - When adjusting the plan
```
<plan_update>
Adding data cleaning step because missing values were found.
</plan_update>
```

### <code> - Python code to execute
One focused code block per response. Variables persist between executions.

### <answer> - Final answer (ONLY when ALL steps show [x])
Comprehensive summary of findings, insights, and recommendations.

## Critical Rules

1. **ALWAYS include <plan>** in every response showing current status
2. **Mark steps [x]** immediately when completed
3. **NEVER use <answer>** if ANY step shows [ ]
4. **Be THOROUGH**: Include steps for:
   - Data loading and exploration
   - Data cleaning and preprocessing
   - Feature engineering
   - Model building/analysis
   - Model evaluation and metrics
   - Visualizations and charts
   - Summary and recommendations
5. **Adjust plan** when results suggest different approach or errors occur
6. **One code block per response**: Execute one step at a time

## Available Libraries
pandas, numpy, matplotlib, seaborn, scikit-learn, scipy, statsmodels, pycaret

## Important for Visualizations
- Always use plt.savefig('filename.png') to save charts to disk
- Then call plt.show() to display
- Example:
  ```python
  plt.figure(figsize=(10, 6))
  plt.plot(data)
  plt.savefig('my_chart.png', dpi=150, bbox_inches='tight')
  plt.show()
  ```
'''


class AgentEngine:
    """Core engine that runs the agent loop.

    Handles:
    - LLM communication with fallbacks
    - Plan state management
    - Code execution via Jupyter kernel
    - Event streaming for UI updates

    Example:
        engine = AgentEngine(config, executor, logger)

        # Run with streaming
        for event in engine.run_stream("Analyze sales data"):
            print(event.type, event.message)

        # Or run synchronously
        result = engine.run("Analyze sales data")
    """

    # Stop sequences for LLM
    STOP_SEQUENCES = ["</code>", "</answer>"]

    def __init__(
        self,
        config: AgentConfig,
        executor: JupyterExecutor,
        logger: AgentLogger,
        notebook_builder: Optional[NotebookBuilder] = None,
        event_callback: Optional[Callable[[AgentEvent], Any]] = None,
        run_logger: Optional["RunLogger"] = None,
    ) -> None:
        """Initialize the engine.

        Args:
            config: Agent configuration
            executor: Jupyter executor for code execution
            logger: Logger instance
            notebook_builder: Optional notebook builder for tracking
            event_callback: Optional callback for streaming events
            run_logger: Optional run logger for comprehensive logging
        """
        self.config = config
        self.executor = executor
        self.logger = logger
        self.notebook = notebook_builder
        self.event_callback = event_callback
        self.run_logger = run_logger

        self.messages: list[Message] = []
        self.current_plan: Optional[PlanState] = None
        self.round_num = 0
        self.answer: Optional[str] = None

    def _emit(
        self,
        event_type: EventType,
        message: Optional[str] = None,
        **kwargs: Any,
    ) -> AgentEvent:
        """Emit an event to the callback and logger."""
        event = self.logger.emit_event(event_type, message, **kwargs)
        if self.event_callback:
            self.event_callback(event)
        return event

    def _call_llm(self, messages: list[dict]) -> str:
        """Call the LLM with automatic fallbacks.

        Handles various provider-specific issues:
        - stop parameter not supported
        - temperature not supported
        - max_tokens vs max_completion_tokens

        Args:
            messages: Chat messages

        Returns:
            LLM response text
        """
        return self._call_llm_with_fallbacks(
            messages,
            use_stop=True,
            use_temperature=True,
            use_max_tokens=True,
        )

    def _call_llm_with_fallbacks(
        self,
        messages: list[dict],
        use_stop: bool = True,
        use_temperature: bool = True,
        use_max_tokens: bool = True,
    ) -> str:
        """Call LLM with recursive fallbacks for parameter issues.

        Args:
            messages: Chat messages
            use_stop: Whether to use stop sequences
            use_temperature: Whether to use temperature
            use_max_tokens: Whether to use max_tokens (vs max_completion_tokens)

        Returns:
            LLM response text
        """
        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
        }

        if use_stop:
            kwargs["stop"] = self.STOP_SEQUENCES
        if use_temperature:
            kwargs["temperature"] = self.config.temperature
        if use_max_tokens:
            kwargs["max_tokens"] = self.config.max_tokens
        else:
            kwargs["max_completion_tokens"] = self.config.max_tokens

        try:
            response = completion(**kwargs)
            content = response.choices[0].message.content or ""

            # If stop was disabled, manually truncate at stop sequences
            if not use_stop:
                for stop_seq in self.STOP_SEQUENCES:
                    if stop_seq in content:
                        idx = content.index(stop_seq)
                        content = content[: idx + len(stop_seq)]
                        break

            return content

        except Exception as e:
            error_msg = str(e).lower()

            # Handle stop parameter not supported
            if use_stop and "stop" in error_msg:
                self.logger.warning(
                    f"Provider doesn't support 'stop', retrying without it"
                )
                return self._call_llm_with_fallbacks(
                    messages,
                    use_stop=False,
                    use_temperature=use_temperature,
                    use_max_tokens=use_max_tokens,
                )

            # Handle temperature not supported
            if use_temperature and "temperature" in error_msg:
                self.logger.warning(
                    f"Provider doesn't support 'temperature', retrying without it"
                )
                return self._call_llm_with_fallbacks(
                    messages,
                    use_stop=use_stop,
                    use_temperature=False,
                    use_max_tokens=use_max_tokens,
                )

            # Handle max_tokens vs max_completion_tokens
            if use_max_tokens and "max_tokens" in error_msg:
                self.logger.warning(
                    f"Provider requires 'max_completion_tokens', retrying"
                )
                return self._call_llm_with_fallbacks(
                    messages,
                    use_stop=use_stop,
                    use_temperature=use_temperature,
                    use_max_tokens=False,
                )

            raise

    def _should_reject_answer(self, plan: Optional[PlanState]) -> bool:
        """Check if the answer should be rejected because plan isn't complete.

        Args:
            plan: Current plan state

        Returns:
            True if answer should be rejected
        """
        if not plan:
            return False

        pending = [s for s in plan.steps if not s.completed]
        if pending:
            self.logger.warning(
                f"Rejecting early answer: {len(pending)} steps still pending"
            )
            return True
        return False

    def _execute_code(self, code: str, step_desc: str = "") -> ExecutionResult:
        """Execute code and track for notebook generation.

        Args:
            code: Python code to execute
            step_desc: Description of current step

        Returns:
            Execution result
        """
        result = self.executor.execute(code)

        # Track for notebook
        if self.notebook:
            self.notebook.track_execution(code, result, step_desc)

        return result

    def _build_context_message(
        self,
        code: str,
        result: ExecutionResult,
    ) -> str:
        """Build context message from execution result.

        Args:
            code: Executed code
            result: Execution result

        Returns:
            Formatted context message
        """
        output = result.output
        # Clean ANSI codes
        output = PlanParser.clean_ansi(output)

        # Truncate if too long
        max_output = 4000
        if len(output) > max_output:
            output = output[:max_output] + f"\n... (truncated, {len(output)} chars total)"

        parts = [f"Code executed:\n```python\n{code}\n```\n"]

        if result.success:
            parts.append(f"Output:\n{output}")
            if result.images:
                parts.append(f"\n[{len(result.images)} image(s) generated]")
        else:
            parts.append(f"Error:\n{output}")

        return "\n".join(parts)

    def run(self, task: str) -> str:
        """Run the agent loop synchronously.

        Args:
            task: User task to accomplish

        Returns:
            Final answer string
        """
        # Consume the generator
        for _ in self.run_stream(task):
            pass
        return self.answer or "No answer generated"

    def run_stream(self, task: str) -> Generator[AgentEvent, None, None]:
        """Run the agent loop with streaming events.

        Args:
            task: User task to accomplish

        Yields:
            AgentEvent for each significant event
        """
        self._emit(EventType.AGENT_STARTED, f"Starting task: {task}")

        # Initialize messages
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Task: {task}"},
        ]

        self.round_num = 0
        self.answer = None

        while self.round_num < self.config.max_rounds:
            self.round_num += 1
            self.logger.set_round(self.round_num)

            yield self._emit(
                EventType.ROUND_STARTED,
                f"Round {self.round_num}/{self.config.max_rounds}",
            )

            # Get LLM response
            yield self._emit(EventType.LLM_CALL_STARTED)

            # Log LLM request
            if self.run_logger:
                self.run_logger.log_round_start(self.round_num)
                prompt = self.messages[-1].get("content", "") if self.messages else ""
                self.run_logger.log_llm_request(
                    prompt=prompt,
                    model=self.config.model,
                    messages=self.messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens,
                )

            try:
                import time
                start_time = time.time()
                response = self._call_llm(self.messages)
                latency_ms = (time.time() - start_time) * 1000

                # Log LLM response
                if self.run_logger:
                    self.run_logger.log_llm_response(
                        response=response,
                        latency_ms=latency_ms,
                        model=self.config.model,
                    )
            except Exception as e:
                if self.run_logger:
                    self.run_logger.log_error(str(e), error_type="llm_error")
                yield self._emit(EventType.AGENT_ERROR, f"LLM error: {e}")
                break

            yield self._emit(EventType.LLM_CALL_FINISHED, response[:200] + "...")

            # Parse response
            new_plan = PlanParser.parse_plan(response)
            code = PlanParser.extract_code(response)
            thinking = PlanParser.extract_thinking(response)
            has_answer = PlanParser.has_final_answer(response)

            # Update plan state
            if new_plan:
                plan_update = PlanParser.extract_plan_update(response)
                self.current_plan = new_plan
                yield self._emit(
                    EventType.PLAN_UPDATED,
                    plan_update,
                    plan=new_plan,
                )

                # Log plan update
                if self.run_logger:
                    self.run_logger.log_plan_update(
                        plan_text=new_plan.raw_text,
                        completed_steps=new_plan.completed_steps,
                        total_steps=new_plan.total_steps,
                        reason=plan_update,
                    )

                if self.logger.verbose:
                    self.logger.print_plan(new_plan.raw_text)

            # Log thinking
            if thinking:
                if self.run_logger:
                    self.run_logger.log_thinking(thinking)
                if self.logger.verbose:
                    self.logger.print_status("💭", f"Thinking: {thinking[:100]}...")

            # Check for final answer
            if has_answer:
                # Validate that plan is complete
                if self._should_reject_answer(self.current_plan):
                    # Log rejection
                    if self.run_logger:
                        self.run_logger.log_answer(
                            answer=PlanParser.extract_answer(response) or "",
                            accepted=False,
                            rejection_reason="Plan not complete - pending steps remain",
                        )
                    # Ask agent to continue
                    self.messages.append({"role": "assistant", "content": response})
                    self.messages.append({
                        "role": "user",
                        "content": (
                            "Please complete all remaining plan steps before providing "
                            "the final answer. Some steps are still marked as [ ]."
                        ),
                    })
                    continue

                self.answer = PlanParser.extract_answer(response)
                # Log accepted answer
                if self.run_logger:
                    self.run_logger.log_answer(answer=self.answer or "", accepted=True)
                yield self._emit(EventType.ANSWER_ACCEPTED, self.answer)
                break

            # Execute code if present
            if code:
                yield self._emit(EventType.CODE_EXECUTING, code[:100] + "...")

                if self.logger.verbose:
                    self.logger.print_code(code)

                # Get current step description
                step_desc = ""
                if self.current_plan:
                    current_step = self.current_plan.current_step
                    if current_step:
                        step_desc = current_step.description

                import time
                exec_start = time.time()
                result = self._execute_code(code, step_desc)
                exec_time_ms = (time.time() - exec_start) * 1000

                # Log code execution
                if self.run_logger:
                    self.run_logger.log_code_execution(
                        code=code,
                        success=result.success,
                        output=result.output,
                        error=result.error,
                        images_count=len(result.images),
                        execution_time_ms=exec_time_ms,
                    )

                if result.success:
                    yield self._emit(
                        EventType.CODE_SUCCESS,
                        result.output[:500] if result.output else "(no output)",
                    )
                else:
                    yield self._emit(
                        EventType.CODE_FAILED,
                        result.output[:500] if result.output else "(no output)",
                    )

                if self.logger.verbose:
                    if result.success:
                        self.logger.print_output(result.output)
                    else:
                        self.logger.print_error(result.output)

                # Add context to conversation
                context = self._build_context_message(code, result)
                self.messages.append({"role": "assistant", "content": response})
                self.messages.append({"role": "user", "content": context})

                # Save notebook incrementally
                if self.notebook:
                    self.notebook.save_incremental()

            else:
                # No code, just add response and prompt to continue
                self.messages.append({"role": "assistant", "content": response})
                self.messages.append({
                    "role": "user",
                    "content": "Please continue with the next step of your plan.",
                })

            # Log round end
            if self.run_logger:
                self.run_logger.log_round_end(self.round_num)

            yield self._emit(EventType.ROUND_FINISHED)

        # Handle max rounds reached
        if self.round_num >= self.config.max_rounds and not self.answer:
            self.answer = f"Max rounds ({self.config.max_rounds}) reached without completion."
            yield self._emit(EventType.AGENT_ERROR, self.answer)

        yield self._emit(EventType.AGENT_FINISHED, self.answer)

    def get_state(self) -> dict[str, Any]:
        """Get current engine state for persistence.

        Returns:
            State dictionary
        """
        return {
            "messages": self.messages,
            "round_num": self.round_num,
            "current_plan": self.current_plan.model_dump() if self.current_plan else None,
            "answer": self.answer,
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        """Restore engine state from persistence.

        Args:
            state: State dictionary
        """
        self.messages = state.get("messages", [])
        self.round_num = state.get("round_num", 0)
        if state.get("current_plan"):
            self.current_plan = PlanState(**state["current_plan"])
        self.answer = state.get("answer")
