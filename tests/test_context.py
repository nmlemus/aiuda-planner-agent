"""Tests for RunContext class."""

import pytest
import tempfile
import shutil
from pathlib import Path

from dsagent.core.context import RunContext


class TestRunContext:
    """Tests for RunContext workspace management."""

    def test_creates_directory_structure(self, tmp_path):
        """Test that RunContext creates the correct directory structure."""
        context = RunContext(workspace=tmp_path)

        # Check that all directories were created
        assert context.run_path.exists()
        assert context.data_path.exists()
        assert context.notebooks_path.exists()
        assert context.artifacts_path.exists()
        assert context.logs_path.exists()

    def test_run_id_auto_generated(self, tmp_path):
        """Test that run_id is auto-generated if not provided."""
        context = RunContext(workspace=tmp_path)

        # Run ID should be in format: YYYYMMDD_HHMMSS_xxxxxx
        assert context.run_id is not None
        assert len(context.run_id) > 10
        parts = context.run_id.split("_")
        assert len(parts) == 3
        assert len(parts[0]) == 8  # YYYYMMDD
        assert len(parts[1]) == 6  # HHMMSS
        assert len(parts[2]) == 6  # short uuid

    def test_custom_run_id(self, tmp_path):
        """Test that custom run_id is used when provided."""
        custom_id = "my-custom-run-123"
        context = RunContext(workspace=tmp_path, run_id=custom_id)

        assert context.run_id == custom_id
        assert context.run_path == tmp_path / "runs" / custom_id

    def test_paths_are_correct(self, tmp_path):
        """Test that all paths are correctly computed."""
        context = RunContext(workspace=tmp_path, run_id="test-run")

        assert context.run_path == tmp_path / "runs" / "test-run"
        assert context.data_path == tmp_path / "runs" / "test-run" / "data"
        assert context.notebooks_path == tmp_path / "runs" / "test-run" / "notebooks"
        assert context.artifacts_path == tmp_path / "runs" / "test-run" / "artifacts"
        assert context.logs_path == tmp_path / "runs" / "test-run" / "logs"

    def test_log_paths(self, tmp_path):
        """Test that log file paths are correct."""
        context = RunContext(workspace=tmp_path, run_id="test-run")

        assert context.run_log_path == tmp_path / "runs" / "test-run" / "logs" / "run.log"
        assert context.events_log_path == tmp_path / "runs" / "test-run" / "logs" / "events.jsonl"

    def test_get_artifact_path(self, tmp_path):
        """Test get_artifact_path method."""
        context = RunContext(workspace=tmp_path, run_id="test-run")

        artifact_path = context.get_artifact_path("chart.png")
        assert artifact_path == tmp_path / "runs" / "test-run" / "artifacts" / "chart.png"

    def test_get_notebook_path(self, tmp_path):
        """Test get_notebook_path method."""
        context = RunContext(workspace=tmp_path, run_id="test-run")

        notebook_path = context.get_notebook_path("analysis.ipynb")
        assert notebook_path == tmp_path / "runs" / "test-run" / "notebooks" / "analysis.ipynb"

    def test_to_dict(self, tmp_path):
        """Test to_dict serialization."""
        context = RunContext(workspace=tmp_path, run_id="test-run")

        d = context.to_dict()
        assert d["run_id"] == "test-run"
        assert "workspace" in d
        assert "run_path" in d
        assert "data_path" in d
        assert "notebooks_path" in d
        assert "artifacts_path" in d
        assert "logs_path" in d
        assert "start_time" in d

    def test_no_create_dirs_option(self, tmp_path):
        """Test that directories are not created when create_dirs=False."""
        context = RunContext(workspace=tmp_path, run_id="no-create", create_dirs=False)

        # Paths should be set but not created
        assert context.run_id == "no-create"
        assert not context.run_path.exists()

    def test_multiple_contexts_isolated(self, tmp_path):
        """Test that multiple contexts have isolated directories."""
        context1 = RunContext(workspace=tmp_path, run_id="run-1")
        context2 = RunContext(workspace=tmp_path, run_id="run-2")

        assert context1.run_path != context2.run_path
        assert context1.data_path != context2.data_path

        # Both should exist
        assert context1.run_path.exists()
        assert context2.run_path.exists()

    def test_repr(self, tmp_path):
        """Test string representation."""
        context = RunContext(workspace=tmp_path, run_id="test-run")

        repr_str = repr(context)
        assert "RunContext" in repr_str
        assert "test-run" in repr_str
