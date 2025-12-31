"""Tests for RunLogger class."""

import pytest
import json
from pathlib import Path

from dsagent.core.context import RunContext
from dsagent.utils.run_logger import RunLogger


class TestRunLogger:
    """Tests for RunLogger comprehensive logging."""

    def test_creates_log_files(self, tmp_path):
        """Test that RunLogger creates log files."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        logger = RunLogger(context)
        logger.close()

        assert context.run_log_path.exists()
        assert context.events_log_path.exists()

    def test_log_llm_request(self, tmp_path):
        """Test logging LLM requests."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        logger = RunLogger(context)

        logger.log_llm_request(
            prompt="Test prompt",
            model="gpt-4o",
            temperature=0.3,
            max_tokens=1000,
        )
        logger.close()

        # Check events.jsonl
        events = _read_events(context.events_log_path)
        llm_events = [e for e in events if e["type"] == "llm_request"]
        assert len(llm_events) == 1
        assert llm_events[0]["data"]["model"] == "gpt-4o"
        assert llm_events[0]["data"]["prompt"] == "Test prompt"

    def test_log_llm_response(self, tmp_path):
        """Test logging LLM responses."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        logger = RunLogger(context)

        logger.log_llm_response(
            response="Test response",
            tokens_used=150,
            latency_ms=1200.5,
            model="gpt-4o",
        )
        logger.close()

        events = _read_events(context.events_log_path)
        llm_events = [e for e in events if e["type"] == "llm_response"]
        assert len(llm_events) == 1
        assert llm_events[0]["data"]["tokens_used"] == 150
        assert llm_events[0]["data"]["latency_ms"] == 1200.5

    def test_log_code_execution_success(self, tmp_path):
        """Test logging successful code execution."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        logger = RunLogger(context)

        logger.log_code_execution(
            code="print('hello')",
            success=True,
            output="hello",
            images_count=0,
            execution_time_ms=50.0,
        )
        logger.close()

        events = _read_events(context.events_log_path)
        code_events = [e for e in events if e["type"] == "code_execution"]
        assert len(code_events) == 1
        assert code_events[0]["data"]["success"] is True
        assert code_events[0]["data"]["code"] == "print('hello')"

    def test_log_code_execution_failure(self, tmp_path):
        """Test logging failed code execution."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        logger = RunLogger(context)

        logger.log_code_execution(
            code="1/0",
            success=False,
            output="",
            error="ZeroDivisionError: division by zero",
            execution_time_ms=10.0,
        )
        logger.close()

        events = _read_events(context.events_log_path)
        code_events = [e for e in events if e["type"] == "code_execution"]
        assert len(code_events) == 1
        assert code_events[0]["data"]["success"] is False
        assert "ZeroDivisionError" in code_events[0]["data"]["error"]

    def test_log_plan_update(self, tmp_path):
        """Test logging plan updates."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        logger = RunLogger(context)

        logger.log_plan_update(
            plan_text="1. [x] Load data\n2. [ ] Analyze",
            completed_steps=1,
            total_steps=2,
            reason="Initial plan",
        )
        logger.close()

        events = _read_events(context.events_log_path)
        plan_events = [e for e in events if e["type"] == "plan_update"]
        assert len(plan_events) == 1
        assert plan_events[0]["data"]["completed_steps"] == 1
        assert plan_events[0]["data"]["total_steps"] == 2

    def test_log_answer_accepted(self, tmp_path):
        """Test logging accepted answer."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        logger = RunLogger(context)

        logger.log_answer(
            answer="The analysis shows...",
            accepted=True,
        )
        logger.close()

        events = _read_events(context.events_log_path)
        answer_events = [e for e in events if e["type"] == "answer"]
        assert len(answer_events) == 1
        assert answer_events[0]["data"]["accepted"] is True

    def test_log_answer_rejected(self, tmp_path):
        """Test logging rejected answer."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        logger = RunLogger(context)

        logger.log_answer(
            answer="Partial answer...",
            accepted=False,
            rejection_reason="Plan not complete",
        )
        logger.close()

        events = _read_events(context.events_log_path)
        answer_events = [e for e in events if e["type"] == "answer"]
        assert len(answer_events) == 1
        assert answer_events[0]["data"]["accepted"] is False
        assert "Plan not complete" in answer_events[0]["data"]["rejection_reason"]

    def test_log_thinking(self, tmp_path):
        """Test logging thinking/reasoning."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        logger = RunLogger(context)

        logger.log_thinking("I need to analyze the data first...")
        logger.close()

        events = _read_events(context.events_log_path)
        thinking_events = [e for e in events if e["type"] == "thinking"]
        assert len(thinking_events) == 1
        assert "analyze" in thinking_events[0]["data"]["thinking"]

    def test_log_error(self, tmp_path):
        """Test logging errors."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        logger = RunLogger(context)

        logger.log_error(
            error="Connection failed",
            error_type="network_error",
            traceback="Traceback...",
        )
        logger.close()

        events = _read_events(context.events_log_path)
        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) == 1
        assert error_events[0]["data"]["error_type"] == "network_error"

    def test_log_round_markers(self, tmp_path):
        """Test logging round start/end markers."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        logger = RunLogger(context)

        logger.log_round_start(1)
        logger.log_round_end(1)
        logger.log_round_start(2)
        logger.log_round_end(2)
        logger.close()

        events = _read_events(context.events_log_path)
        round_starts = [e for e in events if e["type"] == "round_start"]
        round_ends = [e for e in events if e["type"] == "round_end"]
        assert len(round_starts) == 2
        assert len(round_ends) == 2

    def test_log_artifact_saved(self, tmp_path):
        """Test logging artifact saves."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        logger = RunLogger(context)

        logger.log_artifact_saved(
            artifact_type="image",
            path="/path/to/chart.png",
            size_bytes=12345,
        )
        logger.close()

        events = _read_events(context.events_log_path)
        artifact_events = [e for e in events if e["type"] == "artifact_saved"]
        assert len(artifact_events) == 1
        assert artifact_events[0]["data"]["artifact_type"] == "image"

    def test_session_start_end_events(self, tmp_path):
        """Test that session start/end events are logged."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        logger = RunLogger(context)
        logger.close()

        events = _read_events(context.events_log_path)
        session_starts = [e for e in events if e["type"] == "session_start"]
        session_ends = [e for e in events if e["type"] == "session_end"]
        assert len(session_starts) == 1
        assert len(session_ends) == 1
        assert session_starts[0]["data"]["run_id"] == "test-run"

    def test_event_ids_sequential(self, tmp_path):
        """Test that event IDs are sequential."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        logger = RunLogger(context)

        logger.log_thinking("thought 1")
        logger.log_thinking("thought 2")
        logger.log_thinking("thought 3")
        logger.close()

        events = _read_events(context.events_log_path)
        event_ids = [e["event_id"] for e in events]
        assert event_ids == sorted(event_ids)
        assert len(set(event_ids)) == len(event_ids)  # All unique

    def test_round_number_tracked(self, tmp_path):
        """Test that round number is tracked in events."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        logger = RunLogger(context)

        logger.set_round(5)
        logger.log_thinking("thought in round 5")
        logger.close()

        events = _read_events(context.events_log_path)
        thinking_events = [e for e in events if e["type"] == "thinking"]
        assert thinking_events[0]["round"] == 5

    def test_context_manager(self, tmp_path):
        """Test RunLogger as context manager."""
        context = RunContext(workspace=tmp_path, run_id="test-run")

        with RunLogger(context) as logger:
            logger.log_thinking("test thought")

        # Files should exist after context manager exits
        assert context.run_log_path.exists()
        assert context.events_log_path.exists()

    def test_run_log_human_readable(self, tmp_path):
        """Test that run.log contains human-readable content."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        logger = RunLogger(context)

        logger.log_llm_request(prompt="Test", model="gpt-4o")
        logger.log_code_execution(code="print(1)", success=True, output="1")
        logger.close()

        log_content = context.run_log_path.read_text()
        assert "LLM REQUEST" in log_content
        assert "gpt-4o" in log_content
        assert "CODE SUCCESS" in log_content


def _read_events(path: Path) -> list:
    """Helper to read events from JSONL file."""
    events = []
    with open(path, "r") as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    return events
