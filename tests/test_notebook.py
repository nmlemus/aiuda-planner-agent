"""Tests for NotebookBuilder with RunContext."""

import pytest
import json
from pathlib import Path

from aiuda_planner.core.context import RunContext
from aiuda_planner.utils.notebook import NotebookBuilder, ExecutionTracker
from aiuda_planner.schema.models import ExecutionResult


class TestNotebookBuilderWithContext:
    """Tests for NotebookBuilder with RunContext integration."""

    def test_notebook_saved_to_context_path(self, tmp_path):
        """Test that notebook is saved to context notebooks path."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        builder = NotebookBuilder(task="Test task", context=context)

        notebook_path = builder.save("test.ipynb")

        assert notebook_path.exists()
        assert notebook_path.parent == context.notebooks_path
        assert notebook_path.name == "test.ipynb"

    def test_images_saved_to_artifacts(self, tmp_path):
        """Test that images are saved to artifacts directory."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        builder = NotebookBuilder(task="Test task", context=context)

        # Simulate execution with image
        import base64
        test_image = base64.b64encode(b"fake png data").decode()
        result = ExecutionResult(
            success=True,
            stdout="output",
            images=[{"mime": "image/png", "data": test_image}],
        )

        builder.track_execution("plt.plot([1,2,3])", result, "Plot data")

        # Check that image was saved
        images = list(context.artifacts_path.glob("*.png"))
        assert len(images) == 1

    def test_legacy_workspace_still_works(self, tmp_path):
        """Test that legacy workspace parameter still works."""
        builder = NotebookBuilder(task="Test task", workspace=tmp_path)

        notebook_path = builder.save("legacy.ipynb")

        # Should save to workspace/generated/
        assert notebook_path.exists()
        assert "generated" in str(notebook_path)

    def test_clean_notebook_uses_context_paths(self, tmp_path):
        """Test that clean notebook generation uses context paths."""
        context = RunContext(workspace=tmp_path, run_id="test-run")
        builder = NotebookBuilder(task="Test task", context=context)

        # Track some executions
        result = ExecutionResult(success=True, stdout="42")
        builder.track_execution("print(40+2)", result, "Calculate")

        # Generate clean notebook
        clean = builder.generate_clean_notebook(answer="The answer is 42")
        notebook_path = clean.save("clean.ipynb")

        assert notebook_path.exists()
        assert notebook_path.parent == context.notebooks_path


class TestExecutionTracker:
    """Tests for ExecutionTracker."""

    def test_tracks_executions(self):
        """Test that executions are tracked."""
        tracker = ExecutionTracker()

        tracker.add_execution(
            code="import pandas as pd\ndf = pd.read_csv('data.csv')",
            success=True,
            output="",
            images=[],
            step_desc="Load data",
        )

        assert len(tracker.records) == 1
        assert tracker.records[0].success is True

    def test_extracts_imports(self):
        """Test import extraction."""
        tracker = ExecutionTracker()

        tracker.add_execution(
            code="import pandas as pd\nimport numpy as np\nprint('hello')",
            success=True,
            output="hello",
            images=[],
        )

        assert "import pandas as pd" in tracker.all_imports
        assert "import numpy as np" in tracker.all_imports

    def test_consolidates_imports(self):
        """Test import consolidation."""
        tracker = ExecutionTracker()

        tracker.add_execution(
            code="import pandas as pd",
            success=True,
            output="",
            images=[],
        )
        tracker.add_execution(
            code="import os\nimport numpy as np",
            success=True,
            output="",
            images=[],
        )

        consolidated = tracker.get_consolidated_imports()
        assert "import os" in consolidated
        assert "import pandas as pd" in consolidated
        assert "import numpy as np" in consolidated

    def test_successful_cells_have_imports_removed(self):
        """Test that successful cells have imports removed."""
        tracker = ExecutionTracker()

        tracker.add_execution(
            code="import pandas as pd\ndf = pd.DataFrame()",
            success=True,
            output="",
            images=[],
        )

        cells = tracker.get_successful_cells()
        assert len(cells) == 1
        assert "import" not in cells[0].code
        assert "DataFrame" in cells[0].code

    def test_failed_cells_not_in_successful(self):
        """Test that failed cells are not included in successful cells."""
        tracker = ExecutionTracker()

        tracker.add_execution(
            code="good_code()",
            success=True,
            output="ok",
            images=[],
        )
        tracker.add_execution(
            code="bad_code()",
            success=False,
            output="Error",
            images=[],
        )

        cells = tracker.get_successful_cells()
        assert len(cells) == 1
        assert "good_code" in cells[0].code
