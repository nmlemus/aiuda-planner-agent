"""Local Jupyter kernel executor.

This module provides a local execution backend using Jupyter's
kernel manager. The kernel runs in the same process/machine as
the agent.

Note: For production use with untrusted code, consider using
DockerExecutor or RemoteExecutor for isolation.
"""

from __future__ import annotations

import queue
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from jupyter_client import KernelManager

from dsagent.kernel.backend import (
    ExecutorBackend,
    ExecutorConfig,
    ExecutorError,
    ExecutorStartError,
    ExecutorNotRunningError,
    ExecutorTimeoutError,
)
from dsagent.kernel.introspector import KernelIntrospector
from dsagent.schema.models import ExecutionResult
from dsagent.session.models import KernelSnapshot

if TYPE_CHECKING:
    from dsagent.utils.logger import AgentLogger


class LocalExecutor(ExecutorBackend):
    """Executes Python code in a local Jupyter kernel.

    The kernel maintains state between executions, allowing variables,
    imports, and objects to persist across multiple code blocks.

    This executor runs in the same process space as the agent,
    which means there's no isolation from potentially dangerous code.
    For production deployments with untrusted code, consider using
    DockerExecutor or RemoteExecutor instead.

    Example:
        config = ExecutorConfig(workspace="./workspace", timeout=300)
        executor = LocalExecutor(config)
        executor.start()

        result = executor.execute("import pandas as pd")
        result = executor.execute("df = pd.DataFrame({'a': [1,2,3]})")

        state = executor.get_kernel_state()
        print(state.get_context_summary())

        executor.shutdown()

    Or using context manager:
        with LocalExecutor(config) as executor:
            result = executor.execute("print('hello')")
    """

    def __init__(
        self,
        config: Optional[ExecutorConfig] = None,
        logger: Optional["AgentLogger"] = None,
    ):
        """Initialize the local executor.

        Args:
            config: Executor configuration
            logger: Optional logger for events
        """
        super().__init__(config)
        self.logger = logger
        self._km: Optional[KernelManager] = None
        self._kc = None
        self._introspector: Optional[KernelIntrospector] = None

    @property
    def is_running(self) -> bool:
        """Check if the kernel is running."""
        return self._started and self._km is not None

    @property
    def workspace(self) -> Path:
        """Get the workspace path."""
        return self.config.workspace

    def start(self) -> None:
        """Start the Jupyter kernel.

        Raises:
            ExecutorStartError: If kernel fails to start
        """
        if self._started:
            return

        try:
            # Ensure workspace exists
            self.workspace.mkdir(parents=True, exist_ok=True)

            # Start kernel
            self._km = KernelManager(kernel_name="python3")
            self._km.start_kernel(cwd=str(self.workspace))
            self._kc = self._km.client()
            self._kc.start_channels()
            self._kc.wait_for_ready(timeout=60)

            # Initialize kernel environment
            self._initialize_kernel()

            self._started = True

            # Create introspector
            self._introspector = KernelIntrospector(
                execute_fn=self.execute,
                silent_fn=self.execute_silent,
            )

            if self.logger:
                self.logger.info(f"Jupyter kernel started in {self.workspace}")

        except Exception as e:
            self._cleanup()
            raise ExecutorStartError(f"Failed to start kernel: {e}") from e

    def _initialize_kernel(self) -> None:
        """Initialize kernel with standard setup code."""
        workspace_path = str(self.workspace).replace("\\", "\\\\")

        setup_code = f"""
import warnings
warnings.filterwarnings('ignore')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.ioff()

import os
os.chdir('{workspace_path}')
"""
        self._execute_silent(setup_code)

        # Run custom init code if provided
        if self.config.init_code:
            self._execute_silent(self.config.init_code)

    def _drain_iopub(self) -> None:
        """Drain any pending messages from the iopub channel."""
        if not self._kc:
            return
        while True:
            try:
                self._kc.get_iopub_msg(timeout=0.1)
            except queue.Empty:
                break

    def _execute_silent(self, code: str) -> bool:
        """Execute code without capturing output.

        Args:
            code: Python code to execute

        Returns:
            True if execution succeeded
        """
        if not self._kc:
            return False

        msg_id = self._kc.execute(code)

        # Wait for shell reply
        while True:
            try:
                msg = self._kc.get_shell_msg(timeout=30)
                if msg["msg_type"] == "execute_reply":
                    status = msg["content"]["status"]
                    break
            except queue.Empty:
                return False

        # Drain iopub to clear any output
        self._drain_iopub()

        return status == "ok"

    def execute_silent(self, code: str) -> bool:
        """Execute code without capturing output.

        Args:
            code: Python code to execute

        Returns:
            True if execution succeeded
        """
        return self._execute_silent(code)

    def execute(self, code: str) -> ExecutionResult:
        """Execute code and capture all outputs.

        Args:
            code: Python code to execute

        Returns:
            ExecutionResult with stdout, stderr, errors, and images

        Raises:
            ExecutorNotRunningError: If kernel is not running
        """
        if not self._kc:
            raise ExecutorNotRunningError("Kernel not started")

        # Clear any stale messages
        self._drain_iopub()

        result = ExecutionResult()
        msg_id = self._kc.execute(code)

        timeout = self.config.timeout

        while True:
            try:
                msg = self._kc.get_iopub_msg(timeout=timeout)
                msg_type = msg["msg_type"]
                content = msg["content"]

                # Only process messages for THIS execution
                parent_msg_id = msg.get("parent_header", {}).get("msg_id")
                if parent_msg_id != msg_id:
                    continue

                if msg_type == "stream":
                    if content["name"] == "stdout":
                        result.stdout += content["text"]
                    elif content["name"] == "stderr":
                        text = content["text"]
                        # Filter out common warnings
                        if not text.startswith("WARNING") and "UserWarning" not in text:
                            result.stderr += text

                elif msg_type == "execute_result":
                    data = content.get("data", {})
                    if "text/plain" in data:
                        result.stdout += data["text/plain"] + "\n"
                    # Capture images
                    for mime in ["image/png", "image/jpeg", "image/svg+xml"]:
                        if mime in data:
                            result.images.append({"mime": mime, "data": data[mime]})

                elif msg_type == "display_data":
                    data = content.get("data", {})
                    if "text/plain" in data:
                        result.stdout += data["text/plain"] + "\n"
                    for mime in ["image/png", "image/jpeg", "image/svg+xml"]:
                        if mime in data:
                            result.images.append({"mime": mime, "data": data[mime]})

                elif msg_type == "error":
                    result.error = "\n".join(content.get("traceback", []))
                    result.success = False

                elif msg_type == "status":
                    if content["execution_state"] == "idle":
                        break

            except queue.Empty:
                result.error = f"Timeout after {timeout}s"
                result.success = False
                break
            except Exception as e:
                result.error = str(e)
                result.success = False
                break

        # Check shell reply for execution status
        try:
            reply = self._kc.get_shell_msg(timeout=10)
            if reply["content"]["status"] == "error":
                result.success = False
        except Exception:
            pass

        return result

    def get_kernel_state(self) -> KernelSnapshot:
        """Get the current state of the kernel.

        Returns:
            KernelSnapshot with variables, DataFrames, imports, etc.
        """
        if not self._introspector or not self.is_running:
            return KernelSnapshot()

        result = self._introspector.introspect()
        return result.to_kernel_snapshot()

    def get_variables(self) -> list[str]:
        """Get list of defined variables in the kernel.

        Returns:
            List of variable names
        """
        state = self.get_kernel_state()
        return list(state.variables.keys())

    def _cleanup(self) -> None:
        """Clean up kernel resources."""
        if self._kc:
            try:
                self._kc.stop_channels()
            except Exception:
                pass
        if self._km:
            try:
                self._km.shutdown_kernel(now=True)
            except Exception:
                pass
        self._kc = None
        self._km = None
        self._started = False
        self._introspector = None

    def shutdown(self) -> None:
        """Shutdown the Jupyter kernel."""
        self._cleanup()

        if self.logger:
            self.logger.info("Jupyter kernel stopped")

    def reset(self) -> None:
        """Reset the kernel to a clean state.

        This is more efficient than restart for clearing variables
        while keeping imports.
        """
        if not self.is_running:
            self.start()
            return

        # Clear all user variables but keep standard imports
        clear_code = """
# Get all user-defined variables
_to_delete = [
    name for name in list(globals().keys())
    if not name.startswith('_')
    and name not in ('In', 'Out', 'get_ipython', 'exit', 'quit')
]
for _name in _to_delete:
    del globals()[_name]
del _to_delete, _name
"""
        self._execute_silent(clear_code)


# Backward compatibility alias
JupyterExecutor = LocalExecutor
