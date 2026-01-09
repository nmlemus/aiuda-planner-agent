"""Notebook generation utilities for the AI Planner Agent."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any, TYPE_CHECKING

from dsagent.schema.models import (
    ExecutionResult,
    ExecutionRecord,
    PlanState,
)

if TYPE_CHECKING:
    from dsagent.core.context import RunContext

logger = logging.getLogger(__name__)


class ExecutionTracker:
    """Tracks all code executions for smart notebook generation.

    This enables the "hybrid" approach where:
    - ALL imports are collected (from both successful and failed cells)
    - Only successful cells are included in the final notebook
    - Imports are consolidated at the top

    This ensures the generated notebook is runnable, even if some cells
    failed during agent execution.
    """

    # Common stdlib modules for sorting imports
    STDLIB_MODULES = {
        "os", "sys", "re", "json", "datetime", "pathlib",
        "collections", "itertools", "functools", "typing",
        "warnings", "math", "random", "time", "copy",
        "io", "pickle", "csv", "logging", "abc",
    }

    def __init__(self) -> None:
        """Initialize the tracker."""
        self.records: List[ExecutionRecord] = []
        self.all_imports: set[str] = set()
        self.used_imports: set[str] = set()

    def add_execution(
        self,
        code: str,
        success: bool,
        output: str,
        images: List[Dict[str, Any]],
        step_desc: str = "",
    ) -> None:
        """Record a code execution.

        Args:
            code: The executed Python code
            success: Whether execution succeeded
            output: Execution output
            images: Any captured images
            step_desc: Description of the current plan step
        """
        record = ExecutionRecord(
            code=code,
            success=success,
            output=output,
            images=images,
            step_description=step_desc,
        )
        self.records.append(record)

        # Extract imports from this code
        imports = self._extract_imports(code)
        self.all_imports.update(imports)
        if success:
            self.used_imports.update(imports)

    def _extract_imports(self, code: str) -> set[str]:
        """Extract import statements from code.

        Args:
            code: Python code

        Returns:
            Set of import statements
        """
        imports = set()
        for line in code.split("\n"):
            line = line.strip()
            if line.startswith("import ") or line.startswith("from "):
                # Remove inline comments
                if "#" in line:
                    line = line[: line.index("#")].strip()
                if line:
                    imports.add(line)
        return imports

    def _remove_imports(self, code: str) -> str:
        """Remove import statements from code.

        Args:
            code: Python code

        Returns:
            Code with imports removed
        """
        lines = []
        for line in code.split("\n"):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                continue
            lines.append(line)
        # Remove leading empty lines
        while lines and not lines[0].strip():
            lines.pop(0)
        return "\n".join(lines)

    def get_consolidated_imports(self) -> str:
        """Get all imports sorted and consolidated.

        Imports are sorted with stdlib first, then third-party.

        Returns:
            Consolidated import statements
        """
        if not self.all_imports:
            return ""

        stdlib = []
        third_party = []

        for imp in sorted(self.all_imports):
            # Get the first module name
            parts = imp.split()
            if len(parts) >= 2:
                first_module = parts[1].split(".")[0].split(",")[0]
                if first_module in self.STDLIB_MODULES:
                    stdlib.append(imp)
                else:
                    third_party.append(imp)
            else:
                third_party.append(imp)

        result = []
        if stdlib:
            result.extend(stdlib)
        if third_party:
            if stdlib:
                result.append("")  # Empty line between groups
            result.extend(third_party)

        return "\n".join(result)

    def get_successful_cells(self) -> List[ExecutionRecord]:
        """Get successful executions with imports removed.

        Returns:
            List of successful ExecutionRecords with clean code
        """
        cells = []
        for record in self.records:
            if record.success:
                clean_code = self._remove_imports(record.code)
                if clean_code.strip():
                    cells.append(
                        ExecutionRecord(
                            code=clean_code,
                            success=True,
                            output=record.output,
                            images=record.images,
                            step_description=record.step_description,
                        )
                    )
        return cells


class NotebookBuilder:
    """Builds Jupyter notebooks from agent execution traces.

    Supports two modes:
    1. Incremental: Add cells as they execute (for live updates)
    2. Clean generation: Generate a polished notebook at the end

    Example:
        # With RunContext (new way)
        context = RunContext(workspace="./workspace")
        builder = NotebookBuilder(task="Analyze data", context=context)

        # Legacy (still supported)
        builder = NotebookBuilder(task="Analyze data", workspace="./workspace")

        # Track executions
        builder.track_execution(code, result, "Step 1")

        # Generate clean notebook at the end
        clean = builder.generate_clean_notebook(final_plan, answer)
        path = clean.save()
    """

    def __init__(
        self,
        task: str,
        workspace: Optional[str | Path] = None,
        context: Optional["RunContext"] = None,
    ) -> None:
        """Initialize the notebook builder.

        Args:
            task: The user's task description
            workspace: Working directory path (legacy, use context instead)
            context: RunContext for new workspace structure
        """
        self.task = task
        self.context = context

        # Determine paths based on context or legacy workspace
        if context:
            self.workspace = context.run_path
            self._notebooks_path = context.notebooks_path
            self._artifacts_path = context.artifacts_path
        else:
            self.workspace = Path(workspace) if workspace else Path("./workspace")
            self._notebooks_path = self.workspace / "generated"
            self._artifacts_path = self.workspace / "images"

        self.cells: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        self.execution_count = 0
        self.tracker = ExecutionTracker()
        self._filename: Optional[str] = None

        # Add header cell
        self._add_markdown(f"""# Agent Analysis Notebook

**Task:** {task}

**Generated:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}

**Agent Type:** Planner Agent (with dynamic task planning)

---
""")

    def _add_markdown(self, content: str) -> None:
        """Add a markdown cell."""
        self.cells.append({
            "cell_type": "markdown",
            "metadata": {},
            "source": [line + "\n" for line in content.split("\n")],
        })

    def _add_code(self, code: str, outputs: Optional[List[Dict]] = None) -> None:
        """Add a code cell."""
        self.execution_count += 1
        self.cells.append({
            "cell_type": "code",
            "metadata": {},
            "source": [line + "\n" for line in code.split("\n")],
            "outputs": outputs or [],
            "execution_count": self.execution_count,
        })

    def track_execution(
        self,
        code: str,
        result: ExecutionResult,
        step_desc: str = "",
    ) -> None:
        """Track an execution for final notebook generation.

        Also saves any generated images to the workspace/images directory.

        Args:
            code: Executed Python code
            result: Execution result
            step_desc: Description of the plan step
        """
        # Save images to disk
        if result.images:
            self._save_images(result.images)

        self.tracker.add_execution(
            code=code,
            success=result.success,
            output=result.output,
            images=result.images,
            step_desc=step_desc,
        )

    def _save_images(self, images: list) -> None:
        """Save images to the artifacts directory.

        Args:
            images: List of image dicts with 'mime' and 'data' keys
        """
        import base64

        self._artifacts_path.mkdir(parents=True, exist_ok=True)

        for i, img in enumerate(images):
            mime = img.get("mime", "image/png")
            data = img.get("data", "")

            # Determine extension from mime type
            ext_map = {
                "image/png": ".png",
                "image/jpeg": ".jpg",
                "image/svg+xml": ".svg",
            }
            ext = ext_map.get(mime, ".png")

            # Generate filename with timestamp
            timestamp = self.start_time.strftime("%H%M%S")
            filename = f"figure_{timestamp}_{self.execution_count}_{i}{ext}"
            filepath = self._artifacts_path / filename

            # Decode and save
            try:
                if mime == "image/svg+xml":
                    filepath.write_text(data)
                else:
                    img_bytes = base64.b64decode(data)
                    filepath.write_bytes(img_bytes)
            except Exception:
                pass  # Silently skip if save fails

    def add_plan(self, plan: PlanState, update_reason: Optional[str] = None) -> None:
        """Add current plan state as markdown.

        Args:
            plan: Current plan state
            update_reason: Optional reason for plan update
        """
        content = "## Current Plan\n\n"
        if update_reason:
            content += f"*Plan updated: {update_reason}*\n\n"
        content += "```\n" + plan.raw_text + "\n```\n"
        content += f"\n**Progress:** {plan.progress} steps completed\n"
        self._add_markdown(content)

    def add_answer(self, answer: str, final_plan: Optional[PlanState] = None) -> None:
        """Add final answer.

        Args:
            answer: The final answer text
            final_plan: Optional final plan state
        """
        if final_plan:
            self._add_markdown(
                f"## Final Plan Status\n\n"
                f"```\n{final_plan.raw_text}\n```\n\n"
                f"**All {final_plan.total_steps} steps completed!**"
            )
        self._add_markdown(f"---\n\n## Final Answer\n\n{answer}")

    def generate_clean_notebook(
        self,
        final_plan: Optional[PlanState] = None,
        answer: Optional[str] = None,
    ) -> "NotebookBuilder":
        """Generate a clean notebook with consolidated imports.

        Creates a new notebook with:
        - All imports consolidated at the top
        - Only successful code cells (imports removed)
        - Final answer and plan status

        Args:
            final_plan: Final plan state
            answer: Final answer text

        Returns:
            New NotebookBuilder with clean notebook
        """
        clean = NotebookBuilder.__new__(NotebookBuilder)
        clean.task = self.task
        clean.workspace = self.workspace
        clean.context = self.context
        clean._notebooks_path = self._notebooks_path
        clean._artifacts_path = self._artifacts_path
        clean.cells = []
        clean.start_time = self.start_time
        clean.execution_count = 0
        clean.tracker = self.tracker
        clean._filename = self._filename

        # Header
        clean._add_markdown(f"""# Agent Analysis Notebook

**Task:** {self.task}

**Generated:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}

**Agent Type:** Planner Agent (with dynamic task planning)

*This notebook was automatically cleaned: imports consolidated, failed cells removed.*

---
""")

        # Consolidated imports
        imports = self.tracker.get_consolidated_imports()
        if imports:
            clean._add_markdown("## Setup & Imports")
            clean._add_code(imports, [])

        # Successful cells
        successful_cells = self.tracker.get_successful_cells()
        if successful_cells:
            clean._add_markdown("## Analysis")

            for record in successful_cells:
                if record.step_description:
                    clean._add_markdown(f"### {record.step_description}")

                outputs = []
                if record.output and record.output != "(No output)":
                    outputs.append({
                        "output_type": "stream",
                        "name": "stdout",
                        "text": [line + "\n" for line in record.output.split("\n")],
                    })
                for img in record.images:
                    outputs.append({
                        "output_type": "display_data",
                        "data": {img["mime"]: img["data"]},
                        "metadata": {},
                    })
                clean._add_code(record.code, outputs)

        # Final answer
        if answer:
            clean.add_answer(answer, final_plan)

        return clean

    def save(self, filename: Optional[str] = None) -> Path:
        """Save the notebook to a file.

        Args:
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Path to the saved notebook
        """
        if filename is None:
            timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
            filename = f"analysis_{timestamp}.ipynb"

        self._filename = filename

        notebook = {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {"name": "python", "version": "3.11.0"},
            },
            "cells": self.cells,
        }

        self._notebooks_path.mkdir(parents=True, exist_ok=True)
        notebook_path = self._notebooks_path / filename

        with open(notebook_path, "w", encoding="utf-8") as f:
            json.dump(notebook, f, indent=2, ensure_ascii=False)

        return notebook_path

    def save_incremental(self) -> Optional[Path]:
        """Save notebook incrementally using the same filename.

        Returns:
            Path to saved notebook, or None if no filename set
        """
        if self._filename:
            return self.save(self._filename)
        return self.save()


class LiveNotebookBuilder(NotebookBuilder):
    """Notebook builder that saves immediately after each cell addition.

    This enables real-time synchronization with Jupyter - as the agent
    executes code, the notebook file is updated and Jupyter can reload it.

    Example:
        builder = LiveNotebookBuilder(
            task="Analyze data",
            workspace="./workspace",
            auto_save=True,  # Save after each operation
        )

        # Each track_execution will immediately save the notebook
        builder.track_execution(code, result, "Step 1")

        # User can open the notebook in Jupyter and see live updates
    """

    def __init__(
        self,
        task: str,
        workspace: Optional[str | Path] = None,
        context: Optional["RunContext"] = None,
        auto_save: bool = True,
        filename: Optional[str] = None,
    ) -> None:
        """Initialize the live notebook builder.

        Args:
            task: The user's task description
            workspace: Working directory path
            context: RunContext for workspace structure
            auto_save: Whether to save after each cell addition
            filename: Fixed filename to use (auto-generated if not provided)
        """
        super().__init__(task=task, workspace=workspace, context=context)
        self.auto_save = auto_save
        self._save_lock = threading.Lock()
        self._last_save_time: Optional[float] = None

        # Initialize with filename if provided
        if filename:
            self._filename = filename
        else:
            # Generate initial filename
            timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
            self._filename = f"live_analysis_{timestamp}.ipynb"

        # Create initial notebook file
        if auto_save:
            self._save_atomic()

    def _save_atomic(self) -> Optional[Path]:
        """Save notebook atomically to prevent corruption.

        Uses a write-to-temp-then-rename pattern for safety.

        Returns:
            Path to saved notebook
        """
        with self._save_lock:
            notebook = {
                "nbformat": 4,
                "nbformat_minor": 5,
                "metadata": {
                    "kernelspec": {
                        "display_name": "Python 3",
                        "language": "python",
                        "name": "python3",
                    },
                    "language_info": {"name": "python", "version": "3.11.0"},
                    "dsagent": {
                        "live": True,
                        "task": self.task,
                        "last_updated": datetime.now().isoformat(),
                    },
                },
                "cells": self.cells,
            }

            self._notebooks_path.mkdir(parents=True, exist_ok=True)
            notebook_path = self._notebooks_path / self._filename
            temp_path = notebook_path.with_suffix(".tmp")

            try:
                # Write to temp file first
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(notebook, f, indent=2, ensure_ascii=False)

                # Atomic rename
                temp_path.replace(notebook_path)
                self._last_save_time = time.time()

                return notebook_path
            except Exception as e:
                logger.error(f"Failed to save notebook: {e}")
                if temp_path.exists():
                    temp_path.unlink()
                return None

    def track_execution(
        self,
        code: str,
        result: ExecutionResult,
        step_desc: str = "",
    ) -> None:
        """Track an execution and immediately save.

        Args:
            code: Executed Python code
            result: Execution result
            step_desc: Description of the plan step
        """
        # Call parent to track
        super().track_execution(code, result, step_desc)

        # Add a visual cell for live viewing
        if step_desc:
            self._add_markdown(f"### {step_desc}")

        outputs = []
        if result.output and result.output.strip():
            outputs.append({
                "output_type": "stream",
                "name": "stdout",
                "text": [line + "\n" for line in result.output.split("\n")],
            })
        for img in result.images:
            outputs.append({
                "output_type": "display_data",
                "data": {img["mime"]: img["data"]},
                "metadata": {},
            })

        status = "✓" if result.success else "✗"
        self._add_code(f"# [{status}] Execution {self.execution_count}\n{code}", outputs)

        # Auto-save if enabled
        if self.auto_save:
            self._save_atomic()

    def add_plan(self, plan: PlanState, update_reason: Optional[str] = None) -> None:
        """Add current plan state and save.

        Args:
            plan: Current plan state
            update_reason: Optional reason for plan update
        """
        super().add_plan(plan, update_reason)
        if self.auto_save:
            self._save_atomic()

    def add_answer(self, answer: str, final_plan: Optional[PlanState] = None) -> None:
        """Add final answer and save.

        Args:
            answer: The final answer text
            final_plan: Optional final plan state
        """
        super().add_answer(answer, final_plan)
        if self.auto_save:
            self._save_atomic()

    def save(self, filename: Optional[str] = None) -> Path:
        """Save the notebook.

        Args:
            filename: Optional filename override

        Returns:
            Path to the saved notebook
        """
        if filename:
            self._filename = filename
        path = self._save_atomic()
        return path or (self._notebooks_path / self._filename)

    def get_notebook_path(self) -> Path:
        """Get the current notebook file path.

        Returns:
            Path to the notebook file
        """
        return self._notebooks_path / self._filename


class NotebookChange:
    """Represents a change detected in a notebook file."""

    def __init__(
        self,
        change_type: str,
        cell_index: Optional[int] = None,
        old_content: Optional[str] = None,
        new_content: Optional[str] = None,
    ):
        """Initialize a notebook change.

        Args:
            change_type: Type of change ('cell_added', 'cell_modified', 'cell_deleted', 'reloaded')
            cell_index: Index of affected cell (if applicable)
            old_content: Previous content (for modifications)
            new_content: New content (for additions/modifications)
        """
        self.change_type = change_type
        self.cell_index = cell_index
        self.old_content = old_content
        self.new_content = new_content
        self.timestamp = datetime.now()

    def __repr__(self) -> str:
        return f"NotebookChange({self.change_type}, cell={self.cell_index})"


class JupyterFileWatcher:
    """Watches a notebook file for external changes (e.g., user edits in Jupyter).

    Uses watchdog for file system monitoring. When changes are detected,
    the callback is invoked with change details.

    Example:
        def on_change(changes: List[NotebookChange]):
            for change in changes:
                print(f"Detected: {change}")

        watcher = JupyterFileWatcher(
            notebook_path=Path("./notebook.ipynb"),
            on_change=on_change,
        )
        watcher.start()

        # ... do other work ...

        watcher.stop()
    """

    def __init__(
        self,
        notebook_path: Path,
        on_change: Callable[[List[NotebookChange]], None],
        debounce_seconds: float = 0.5,
    ):
        """Initialize the file watcher.

        Args:
            notebook_path: Path to the notebook file to watch
            on_change: Callback invoked when changes are detected
            debounce_seconds: Minimum time between change notifications
        """
        self.notebook_path = Path(notebook_path)
        self.on_change = on_change
        self.debounce_seconds = debounce_seconds

        self._observer = None
        self._running = False
        self._last_content: Optional[Dict] = None
        self._last_mtime: float = 0
        self._debounce_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start watching the notebook file."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler, FileModifiedEvent
        except ImportError:
            logger.warning("watchdog not installed. File watching disabled.")
            return

        if self._running:
            return

        # Load initial content
        self._load_current_content()

        # Create event handler
        watcher = self

        class NotebookEventHandler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.is_directory:
                    return
                if Path(event.src_path).name == watcher.notebook_path.name:
                    watcher._on_file_modified()

        self._observer = Observer()
        self._observer.schedule(
            NotebookEventHandler(),
            str(self.notebook_path.parent),
            recursive=False,
        )
        self._observer.start()
        self._running = True
        logger.info(f"Started watching notebook: {self.notebook_path}")

    def stop(self) -> None:
        """Stop watching the notebook file."""
        if self._observer and self._running:
            self._observer.stop()
            self._observer.join(timeout=2.0)
            self._running = False
            logger.info("Stopped watching notebook")

        if self._debounce_timer:
            self._debounce_timer.cancel()
            self._debounce_timer = None

    def _load_current_content(self) -> Optional[Dict]:
        """Load and parse the current notebook content.

        Returns:
            Parsed notebook dict or None if failed
        """
        try:
            if not self.notebook_path.exists():
                return None

            mtime = self.notebook_path.stat().st_mtime
            if mtime == self._last_mtime:
                return self._last_content

            with open(self.notebook_path, "r", encoding="utf-8") as f:
                content = json.load(f)

            self._last_content = content
            self._last_mtime = mtime
            return content
        except Exception as e:
            logger.debug(f"Failed to load notebook: {e}")
            return None

    def _on_file_modified(self) -> None:
        """Handle file modification event with debouncing."""
        with self._lock:
            # Cancel any pending debounce timer
            if self._debounce_timer:
                self._debounce_timer.cancel()

            # Schedule debounced check
            self._debounce_timer = threading.Timer(
                self.debounce_seconds,
                self._check_for_changes,
            )
            self._debounce_timer.start()

    def _check_for_changes(self) -> None:
        """Check for actual changes in notebook content."""
        old_content = self._last_content
        new_content = self._load_current_content()

        if not new_content:
            return

        changes = self._diff_notebooks(old_content, new_content)
        if changes:
            try:
                self.on_change(changes)
            except Exception as e:
                logger.error(f"Error in change callback: {e}")

    def _diff_notebooks(
        self,
        old: Optional[Dict],
        new: Dict,
    ) -> List[NotebookChange]:
        """Compute differences between two notebook states.

        Args:
            old: Previous notebook content
            new: Current notebook content

        Returns:
            List of detected changes
        """
        changes = []

        if old is None:
            # First load - treat as full reload
            changes.append(NotebookChange("reloaded"))
            return changes

        old_cells = old.get("cells", [])
        new_cells = new.get("cells", [])

        # Check for cell count changes
        if len(new_cells) > len(old_cells):
            for i in range(len(old_cells), len(new_cells)):
                cell = new_cells[i]
                source = "".join(cell.get("source", []))
                changes.append(NotebookChange(
                    "cell_added",
                    cell_index=i,
                    new_content=source,
                ))
        elif len(new_cells) < len(old_cells):
            for i in range(len(new_cells), len(old_cells)):
                changes.append(NotebookChange(
                    "cell_deleted",
                    cell_index=i,
                ))

        # Check for cell modifications
        for i in range(min(len(old_cells), len(new_cells))):
            old_source = "".join(old_cells[i].get("source", []))
            new_source = "".join(new_cells[i].get("source", []))

            if old_source != new_source:
                changes.append(NotebookChange(
                    "cell_modified",
                    cell_index=i,
                    old_content=old_source,
                    new_content=new_source,
                ))

        return changes

    @property
    def is_running(self) -> bool:
        """Check if the watcher is running."""
        return self._running


class LiveNotebookSync:
    """Bidirectional sync between agent and Jupyter notebook.

    Combines LiveNotebookBuilder (agent → file) with JupyterFileWatcher
    (file → agent) for full bidirectional synchronization.

    Example:
        sync = LiveNotebookSync(
            task="Analyze sales data",
            workspace="./workspace",
        )
        sync.start()

        # Agent can write
        sync.track_execution(code, result, "Loading data")

        # User edits in Jupyter are detected
        # sync.on_external_change will be called

        sync.stop()
    """

    def __init__(
        self,
        task: str,
        workspace: Optional[str | Path] = None,
        context: Optional["RunContext"] = None,
        on_external_change: Optional[Callable[[List[NotebookChange]], None]] = None,
    ):
        """Initialize bidirectional sync.

        Args:
            task: The user's task description
            workspace: Working directory path
            context: RunContext for workspace structure
            on_external_change: Callback for user edits in Jupyter
        """
        self.builder = LiveNotebookBuilder(
            task=task,
            workspace=workspace,
            context=context,
            auto_save=True,
        )

        self._on_external_change = on_external_change
        self._watcher: Optional[JupyterFileWatcher] = None
        self._ignore_next_change = False

    def start(self) -> Path:
        """Start synchronization and return notebook path.

        Returns:
            Path to the live notebook file
        """
        notebook_path = self.builder.get_notebook_path()

        # Start watching for external changes
        self._watcher = JupyterFileWatcher(
            notebook_path=notebook_path,
            on_change=self._handle_external_change,
        )
        self._watcher.start()

        return notebook_path

    def stop(self) -> None:
        """Stop synchronization."""
        if self._watcher:
            self._watcher.stop()
            self._watcher = None

    def track_execution(
        self,
        code: str,
        result: ExecutionResult,
        step_desc: str = "",
    ) -> None:
        """Track an execution (agent → file).

        Args:
            code: Executed Python code
            result: Execution result
            step_desc: Description of the plan step
        """
        # Temporarily ignore changes caused by our own write
        self._ignore_next_change = True
        self.builder.track_execution(code, result, step_desc)

    def add_plan(self, plan: PlanState, update_reason: Optional[str] = None) -> None:
        """Add current plan state.

        Args:
            plan: Current plan state
            update_reason: Optional reason for plan update
        """
        self._ignore_next_change = True
        self.builder.add_plan(plan, update_reason)

    def add_answer(self, answer: str, final_plan: Optional[PlanState] = None) -> None:
        """Add final answer.

        Args:
            answer: The final answer text
            final_plan: Optional final plan state
        """
        self._ignore_next_change = True
        self.builder.add_answer(answer, final_plan)

    def _handle_external_change(self, changes: List[NotebookChange]) -> None:
        """Handle changes made externally (user in Jupyter).

        Args:
            changes: List of detected changes
        """
        if self._ignore_next_change:
            self._ignore_next_change = False
            return

        # Filter to only user-relevant changes
        user_changes = [
            c for c in changes
            if c.change_type in ("cell_added", "cell_modified")
        ]

        if user_changes and self._on_external_change:
            self._on_external_change(user_changes)

    def get_notebook_path(self) -> Path:
        """Get the notebook file path.

        Returns:
            Path to the notebook file
        """
        return self.builder.get_notebook_path()

    def generate_clean_notebook(
        self,
        final_plan: Optional[PlanState] = None,
        answer: Optional[str] = None,
    ) -> NotebookBuilder:
        """Generate a clean version of the notebook.

        Args:
            final_plan: Final plan state
            answer: Final answer text

        Returns:
            Clean NotebookBuilder
        """
        return self.builder.generate_clean_notebook(final_plan, answer)
