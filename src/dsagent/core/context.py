"""Run context for managing workspace structure per execution."""

from __future__ import annotations

import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Union


class RunContext:
    """Manages the workspace structure for a single agent run.

    Creates an isolated directory structure for each run:
        workspace/
        └── runs/
            └── {run_id}/
                ├── data/          # Input data (copied)
                ├── notebooks/     # Generated notebooks
                ├── artifacts/     # Images, charts, outputs
                └── logs/          # Execution logs
                    ├── run.log        # Human-readable log
                    └── events.jsonl   # Structured events for ML

    Example:
        context = RunContext(workspace="./workspace")
        print(context.run_id)  # e.g., "20231215_143022_abc123"
        print(context.data_path)  # ./workspace/runs/20231215_143022_abc123/data
    """

    def __init__(
        self,
        workspace: str | Path,
        run_id: Optional[str] = None,
        create_dirs: bool = True,
    ) -> None:
        """Initialize the run context.

        Args:
            workspace: Base workspace directory
            run_id: Optional run ID (auto-generated if not provided)
            create_dirs: Whether to create directories immediately
        """
        self.workspace = Path(workspace).resolve()
        self.run_id = run_id or self._generate_run_id()
        self.run_path = self.workspace / "runs" / self.run_id
        self.start_time = datetime.now()

        if create_dirs:
            self._create_directories()

    def _generate_run_id(self) -> str:
        """Generate a unique run ID.

        Format: YYYYMMDD_HHMMSS_shortid
        Example: 20231215_143022_a1b2c3
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        short_id = uuid.uuid4().hex[:6]
        return f"{timestamp}_{short_id}"

    def _create_directories(self) -> None:
        """Create the directory structure for this run."""
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.notebooks_path.mkdir(parents=True, exist_ok=True)
        self.artifacts_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)

    @property
    def data_path(self) -> Path:
        """Path to the data directory for this run."""
        return self.run_path / "data"

    @property
    def notebooks_path(self) -> Path:
        """Path to the notebooks directory for this run."""
        return self.run_path / "notebooks"

    @property
    def artifacts_path(self) -> Path:
        """Path to the artifacts directory (images, charts, etc.)."""
        return self.run_path / "artifacts"

    @property
    def logs_path(self) -> Path:
        """Path to the logs directory."""
        return self.run_path / "logs"

    @property
    def run_log_path(self) -> Path:
        """Path to the human-readable run log."""
        return self.logs_path / "run.log"

    @property
    def events_log_path(self) -> Path:
        """Path to the structured events log (JSONL format)."""
        return self.logs_path / "events.jsonl"

    def get_artifact_path(self, filename: str) -> Path:
        """Get full path for an artifact file.

        Args:
            filename: Name of the artifact file

        Returns:
            Full path to the artifact
        """
        return self.artifacts_path / filename

    def get_notebook_path(self, filename: str) -> Path:
        """Get full path for a notebook file.

        Args:
            filename: Name of the notebook file

        Returns:
            Full path to the notebook
        """
        return self.notebooks_path / filename

    def copy_data(self, source: Union[str, Path]) -> str:
        """Copy data file or directory contents to the run's data folder.

        Args:
            source: Path to a data file or directory

        Returns:
            A description of what was copied

        Raises:
            FileNotFoundError: If the source path does not exist
        """
        source_path = Path(source).resolve()
        if not source_path.exists():
            raise FileNotFoundError(f"Data path does not exist: {source_path}")

        if source_path.is_file():
            dest_file = self.data_path / source_path.name
            shutil.copy2(source_path, dest_file)
            return f"File '{source_path.name}' copied to run"
        else:
            # Copy directory contents (files only, not subdirectories)
            files_copied = 0
            for item in source_path.iterdir():
                if item.is_file():
                    shutil.copy2(item, self.data_path / item.name)
                    files_copied += 1
            return f"Directory '{source_path.name}' ({files_copied} files) copied to run"

    def to_dict(self) -> dict:
        """Convert context to dictionary for serialization."""
        return {
            "run_id": self.run_id,
            "workspace": str(self.workspace),
            "run_path": str(self.run_path),
            "data_path": str(self.data_path),
            "notebooks_path": str(self.notebooks_path),
            "artifacts_path": str(self.artifacts_path),
            "logs_path": str(self.logs_path),
            "start_time": self.start_time.isoformat(),
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"RunContext(run_id='{self.run_id}', path='{self.run_path}')"
