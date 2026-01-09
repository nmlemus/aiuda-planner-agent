"""Tests for live notebook functionality (Phase 6)."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from dsagent.utils.notebook import (
    LiveNotebookBuilder,
    JupyterFileWatcher,
    LiveNotebookSync,
    NotebookChange,
    NotebookBuilder,
)
from dsagent.schema.models import ExecutionResult


class TestLiveNotebookBuilder:
    """Tests for LiveNotebookBuilder class."""

    def test_init_creates_file(self, tmp_path):
        """Test that init creates the notebook file immediately."""
        builder = LiveNotebookBuilder(
            task="Test task",
            workspace=tmp_path,
            auto_save=True,
        )

        notebook_path = builder.get_notebook_path()
        assert notebook_path.exists()

    def test_init_with_custom_filename(self, tmp_path):
        """Test initialization with custom filename."""
        builder = LiveNotebookBuilder(
            task="Test task",
            workspace=tmp_path,
            filename="custom_notebook.ipynb",
        )

        notebook_path = builder.get_notebook_path()
        assert notebook_path.name == "custom_notebook.ipynb"
        assert notebook_path.exists()

    def test_init_auto_save_disabled(self, tmp_path):
        """Test that auto_save=False doesn't create file immediately."""
        builder = LiveNotebookBuilder(
            task="Test task",
            workspace=tmp_path,
            auto_save=False,
        )

        # File should still exist because we call _save_atomic in __init__ if auto_save
        # But with auto_save=False, we skip it
        notebook_path = builder.get_notebook_path()
        # The file won't exist until we call save()
        # Actually checking the code, we still save initially, let me check...
        # Looking at the code - if auto_save=True, we call _save_atomic()
        # So with auto_save=False, the file shouldn't exist
        assert not notebook_path.exists()

    def test_track_execution_saves_immediately(self, tmp_path):
        """Test that track_execution saves the notebook."""
        builder = LiveNotebookBuilder(
            task="Test task",
            workspace=tmp_path,
        )

        initial_mtime = builder.get_notebook_path().stat().st_mtime

        # Wait a bit and track an execution
        time.sleep(0.01)

        result = ExecutionResult(success=True, stdout="Hello", stderr="")
        builder.track_execution("print('Hello')", result, "Step 1")

        # Check file was updated
        new_mtime = builder.get_notebook_path().stat().st_mtime
        assert new_mtime > initial_mtime

    def test_notebook_contains_metadata(self, tmp_path):
        """Test that saved notebook has dsagent metadata."""
        builder = LiveNotebookBuilder(
            task="My analysis task",
            workspace=tmp_path,
        )

        with open(builder.get_notebook_path()) as f:
            notebook = json.load(f)

        assert "dsagent" in notebook["metadata"]
        assert notebook["metadata"]["dsagent"]["live"] is True
        assert notebook["metadata"]["dsagent"]["task"] == "My analysis task"

    def test_cells_added_on_track_execution(self, tmp_path):
        """Test that cells are added when tracking executions."""
        builder = LiveNotebookBuilder(
            task="Test",
            workspace=tmp_path,
        )

        # Initial cells (header markdown)
        with open(builder.get_notebook_path()) as f:
            notebook = json.load(f)
        initial_cell_count = len(notebook["cells"])

        # Track an execution
        result = ExecutionResult(success=True, stdout="42", stderr="")
        builder.track_execution("x = 42\nprint(x)", result, "Calculate")

        # Check new cells were added
        with open(builder.get_notebook_path()) as f:
            notebook = json.load(f)

        assert len(notebook["cells"]) > initial_cell_count

    def test_execution_status_markers(self, tmp_path):
        """Test that success/failure markers are added to cells."""
        builder = LiveNotebookBuilder(
            task="Test",
            workspace=tmp_path,
        )

        # Track successful execution
        result = ExecutionResult(success=True, stdout="ok", stderr="")
        builder.track_execution("print('ok')", result)

        # Track failed execution
        result = ExecutionResult(success=False, stdout="", stderr="Error!")
        builder.track_execution("1/0", result)

        with open(builder.get_notebook_path()) as f:
            notebook = json.load(f)

        # Find code cells and check markers
        code_cells = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        assert len(code_cells) >= 2

        # Check that markers are present
        sources = ["\n".join(c["source"]) for c in code_cells]
        assert any("[✓]" in s for s in sources)
        assert any("[✗]" in s for s in sources)

    def test_add_plan_saves(self, tmp_path):
        """Test that add_plan saves immediately."""
        from dsagent.schema.models import PlanState, PlanStep

        builder = LiveNotebookBuilder(
            task="Test",
            workspace=tmp_path,
        )

        initial_mtime = builder.get_notebook_path().stat().st_mtime
        time.sleep(0.01)

        plan = PlanState(
            steps=[
                PlanStep(number=1, description="Step 1", completed=False),
                PlanStep(number=2, description="Step 2", completed=False),
            ],
            raw_text="1. [ ] Step 1\n2. [ ] Step 2",
        )
        builder.add_plan(plan)

        new_mtime = builder.get_notebook_path().stat().st_mtime
        assert new_mtime > initial_mtime

    def test_atomic_save_safety(self, tmp_path):
        """Test that atomic save doesn't corrupt file on error."""
        builder = LiveNotebookBuilder(
            task="Test",
            workspace=tmp_path,
        )

        # Get initial content
        initial_content = builder.get_notebook_path().read_text()

        # Corrupt the cells temporarily (this shouldn't affect the file)
        builder.cells = [{"invalid": True}]  # Invalid cell structure

        # Save should still work (JSON is valid)
        result = ExecutionResult(success=True, stdout="", stderr="")
        builder.track_execution("pass", result)

        # File should still be valid JSON
        with open(builder.get_notebook_path()) as f:
            notebook = json.load(f)
        assert "cells" in notebook

    def test_get_notebook_path(self, tmp_path):
        """Test get_notebook_path returns correct path."""
        builder = LiveNotebookBuilder(
            task="Test",
            workspace=tmp_path,
            filename="my_notebook.ipynb",
        )

        path = builder.get_notebook_path()
        assert path.name == "my_notebook.ipynb"
        assert "generated" in str(path) or "notebooks" in str(path)


class TestNotebookChange:
    """Tests for NotebookChange class."""

    def test_init(self):
        """Test NotebookChange initialization."""
        change = NotebookChange(
            change_type="cell_modified",
            cell_index=5,
            old_content="old",
            new_content="new",
        )

        assert change.change_type == "cell_modified"
        assert change.cell_index == 5
        assert change.old_content == "old"
        assert change.new_content == "new"
        assert change.timestamp is not None

    def test_repr(self):
        """Test NotebookChange string representation."""
        change = NotebookChange("cell_added", cell_index=3)
        assert "cell_added" in repr(change)
        assert "3" in repr(change)


class TestJupyterFileWatcher:
    """Tests for JupyterFileWatcher class."""

    def test_init(self, tmp_path):
        """Test JupyterFileWatcher initialization."""
        notebook_path = tmp_path / "test.ipynb"
        callback = MagicMock()

        watcher = JupyterFileWatcher(
            notebook_path=notebook_path,
            on_change=callback,
        )

        assert watcher.notebook_path == notebook_path
        assert not watcher.is_running

    def test_start_stop(self, tmp_path):
        """Test start and stop."""
        notebook_path = tmp_path / "test.ipynb"

        # Create initial notebook
        notebook_path.write_text(json.dumps({
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {},
            "cells": [],
        }))

        callback = MagicMock()
        watcher = JupyterFileWatcher(
            notebook_path=notebook_path,
            on_change=callback,
        )

        watcher.start()
        assert watcher.is_running

        watcher.stop()
        assert not watcher.is_running

    def test_stop_idempotent(self, tmp_path):
        """Test that stop can be called multiple times."""
        notebook_path = tmp_path / "test.ipynb"
        notebook_path.write_text("{}")

        watcher = JupyterFileWatcher(
            notebook_path=notebook_path,
            on_change=lambda x: None,
        )

        watcher.stop()  # Not started yet
        watcher.stop()  # Should not raise

    def test_diff_notebooks_cell_added(self):
        """Test detecting added cells."""
        old = {"cells": [{"source": ["a"]}]}
        new = {"cells": [{"source": ["a"]}, {"source": ["b"]}]}

        watcher = JupyterFileWatcher(
            notebook_path=Path("/fake"),
            on_change=lambda x: None,
        )

        changes = watcher._diff_notebooks(old, new)

        assert len(changes) == 1
        assert changes[0].change_type == "cell_added"
        assert changes[0].cell_index == 1

    def test_diff_notebooks_cell_deleted(self):
        """Test detecting deleted cells."""
        old = {"cells": [{"source": ["a"]}, {"source": ["b"]}]}
        new = {"cells": [{"source": ["a"]}]}

        watcher = JupyterFileWatcher(
            notebook_path=Path("/fake"),
            on_change=lambda x: None,
        )

        changes = watcher._diff_notebooks(old, new)

        assert len(changes) == 1
        assert changes[0].change_type == "cell_deleted"
        assert changes[0].cell_index == 1

    def test_diff_notebooks_cell_modified(self):
        """Test detecting modified cells."""
        old = {"cells": [{"source": ["original"]}]}
        new = {"cells": [{"source": ["modified"]}]}

        watcher = JupyterFileWatcher(
            notebook_path=Path("/fake"),
            on_change=lambda x: None,
        )

        changes = watcher._diff_notebooks(old, new)

        assert len(changes) == 1
        assert changes[0].change_type == "cell_modified"
        assert changes[0].old_content == "original"
        assert changes[0].new_content == "modified"

    def test_diff_notebooks_no_changes(self):
        """Test detecting no changes."""
        old = {"cells": [{"source": ["same"]}]}
        new = {"cells": [{"source": ["same"]}]}

        watcher = JupyterFileWatcher(
            notebook_path=Path("/fake"),
            on_change=lambda x: None,
        )

        changes = watcher._diff_notebooks(old, new)
        assert len(changes) == 0

    def test_diff_notebooks_first_load(self):
        """Test first load triggers reload."""
        watcher = JupyterFileWatcher(
            notebook_path=Path("/fake"),
            on_change=lambda x: None,
        )

        changes = watcher._diff_notebooks(None, {"cells": []})

        assert len(changes) == 1
        assert changes[0].change_type == "reloaded"


class TestLiveNotebookSync:
    """Tests for LiveNotebookSync class."""

    def test_init(self, tmp_path):
        """Test LiveNotebookSync initialization."""
        sync = LiveNotebookSync(
            task="Test task",
            workspace=tmp_path,
        )

        assert sync.builder is not None
        assert sync._watcher is None  # Not started yet

    def test_start_creates_watcher(self, tmp_path):
        """Test that start creates file watcher."""
        sync = LiveNotebookSync(
            task="Test task",
            workspace=tmp_path,
        )

        notebook_path = sync.start()

        assert notebook_path.exists()
        assert sync._watcher is not None

        sync.stop()

    def test_stop(self, tmp_path):
        """Test stop cleans up watcher."""
        sync = LiveNotebookSync(
            task="Test task",
            workspace=tmp_path,
        )

        sync.start()
        sync.stop()

        assert sync._watcher is None

    def test_track_execution(self, tmp_path):
        """Test track_execution through sync."""
        sync = LiveNotebookSync(
            task="Test task",
            workspace=tmp_path,
        )

        sync.start()

        result = ExecutionResult(success=True, stdout="output", stderr="")
        sync.track_execution("print('hello')", result, "Test step")

        # Check that notebook was updated
        with open(sync.get_notebook_path()) as f:
            notebook = json.load(f)

        assert len(notebook["cells"]) > 1  # Header + code cell

        sync.stop()

    def test_callback_on_external_change(self, tmp_path):
        """Test that external changes trigger callback."""
        received_changes = []

        def on_change(changes: List[NotebookChange]):
            received_changes.extend(changes)

        sync = LiveNotebookSync(
            task="Test task",
            workspace=tmp_path,
            on_external_change=on_change,
        )

        sync.start()

        # Simulate external change by directly calling the handler
        # (In real use, this would be triggered by file watcher)
        sync._handle_external_change([
            NotebookChange("cell_added", cell_index=5, new_content="new code")
        ])

        assert len(received_changes) == 1
        assert received_changes[0].change_type == "cell_added"

        sync.stop()

    def test_ignores_own_changes(self, tmp_path):
        """Test that own writes don't trigger callback."""
        received_changes = []

        def on_change(changes: List[NotebookChange]):
            received_changes.extend(changes)

        sync = LiveNotebookSync(
            task="Test task",
            workspace=tmp_path,
            on_external_change=on_change,
        )

        sync.start()

        # Track execution sets _ignore_next_change
        result = ExecutionResult(success=True, stdout="", stderr="")
        sync.track_execution("x = 1", result)

        # Simulated callback should be ignored
        sync._handle_external_change([
            NotebookChange("cell_added", cell_index=1)
        ])

        # No changes should be received because we set _ignore_next_change
        assert len(received_changes) == 0

        sync.stop()

    def test_get_notebook_path(self, tmp_path):
        """Test getting notebook path."""
        sync = LiveNotebookSync(
            task="Test task",
            workspace=tmp_path,
        )

        sync.start()
        path = sync.get_notebook_path()

        assert path.suffix == ".ipynb"
        assert path.exists()

        sync.stop()

    def test_generate_clean_notebook(self, tmp_path):
        """Test generating clean notebook through sync."""
        sync = LiveNotebookSync(
            task="Test task",
            workspace=tmp_path,
        )

        sync.start()

        # Track some executions
        result = ExecutionResult(success=True, stdout="1", stderr="")
        sync.track_execution("import os\nprint(1)", result, "Step 1")

        result = ExecutionResult(success=False, stdout="", stderr="error")
        sync.track_execution("1/0", result, "Step 2")

        result = ExecutionResult(success=True, stdout="2", stderr="")
        sync.track_execution("print(2)", result, "Step 3")

        # Generate clean notebook
        clean = sync.generate_clean_notebook()

        assert clean is not None
        assert len(clean.tracker.get_successful_cells()) == 2  # Only successful

        sync.stop()


class TestConversationalAgentWithLiveNotebook:
    """Tests for ConversationalAgent with live notebook enabled."""

    def test_config_enable_live_notebook(self):
        """Test config has enable_live_notebook option."""
        from dsagent.agents.conversational import ConversationalAgentConfig

        config = ConversationalAgentConfig(enable_live_notebook=True)
        assert config.enable_live_notebook is True

    def test_config_enable_notebook_sync(self):
        """Test config has enable_notebook_sync option."""
        from dsagent.agents.conversational import ConversationalAgentConfig

        config = ConversationalAgentConfig(enable_notebook_sync=True)
        assert config.enable_notebook_sync is True

    def test_agent_uses_live_notebook_builder(self, tmp_path):
        """Test that agent uses LiveNotebookBuilder when enabled."""
        from dsagent.agents.conversational import (
            ConversationalAgent,
            ConversationalAgentConfig,
        )
        from dsagent.session import Session

        session = Session.new()
        session._workspace_path = str(tmp_path)
        session._data_path = str(tmp_path / "data")
        session._artifacts_path = str(tmp_path / "artifacts")
        session._notebooks_path = str(tmp_path / "notebooks")

        config = ConversationalAgentConfig(
            workspace=tmp_path,
            enable_live_notebook=True,
        )
        agent = ConversationalAgent(config=config, session=session)
        agent.start()

        # Trigger notebook builder creation
        builder = agent._create_notebook_builder("Test task", tmp_path)

        assert isinstance(builder, LiveNotebookBuilder)
        assert builder.get_notebook_path().exists()

        agent.shutdown()

    def test_get_live_notebook_path_returns_none_without_live_mode(self, tmp_path):
        """Test get_live_notebook_path returns None without live mode."""
        from dsagent.agents.conversational import (
            ConversationalAgent,
            ConversationalAgentConfig,
        )

        config = ConversationalAgentConfig(workspace=tmp_path)
        agent = ConversationalAgent(config=config)
        agent.start()

        assert agent.get_live_notebook_path() is None

        agent.shutdown()

    def test_get_live_notebook_path_returns_path_with_live_mode(self, tmp_path):
        """Test get_live_notebook_path returns path with live mode."""
        from dsagent.agents.conversational import (
            ConversationalAgent,
            ConversationalAgentConfig,
        )
        from dsagent.session import Session

        session = Session.new()
        session._workspace_path = str(tmp_path)
        session._data_path = str(tmp_path / "data")
        session._artifacts_path = str(tmp_path / "artifacts")
        session._notebooks_path = str(tmp_path / "notebooks")

        config = ConversationalAgentConfig(
            workspace=tmp_path,
            enable_live_notebook=True,
        )
        agent = ConversationalAgent(config=config, session=session)
        agent.start()

        # Initialize notebook by creating it
        agent._notebook_builder = agent._create_notebook_builder("Test", tmp_path)

        path = agent.get_live_notebook_path()
        assert path is not None
        assert path.exists()

        agent.shutdown()
