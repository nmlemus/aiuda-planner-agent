"""Notebook generation utilities for the AI Planner Agent."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from dsagent.schema.models import (
    ExecutionResult,
    ExecutionRecord,
    PlanState,
)

if TYPE_CHECKING:
    from dsagent.core.context import RunContext


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
