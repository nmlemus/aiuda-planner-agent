"""Abstract executor backend interface.

This module defines the interface that all execution backends must implement,
allowing for easy swapping between local kernels, Docker containers,
remote Jupyter servers, etc.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from dsagent.schema.models import ExecutionResult
from dsagent.session.models import KernelSnapshot


@dataclass
class ExecutorConfig:
    """Configuration for executor backends.

    This configuration is backend-agnostic and can be used
    to configure any type of executor.
    """

    # Common settings
    workspace: Path = field(default_factory=lambda: Path("./workspace"))
    timeout: int = 300  # seconds

    # Environment settings
    python_version: Optional[str] = None  # e.g., "3.11"
    working_dir: Optional[str] = None

    # Resource limits (for containerized backends)
    memory_limit: Optional[str] = None  # e.g., "2g"
    cpu_limit: Optional[float] = None  # e.g., 1.0

    # Docker settings (for DockerExecutor)
    docker_image: Optional[str] = None
    docker_network: Optional[str] = None

    # Remote settings (for RemoteExecutor)
    jupyter_url: Optional[str] = None
    jupyter_token: Optional[str] = None

    # Initialization code to run on startup
    init_code: Optional[str] = None

    def __post_init__(self):
        if isinstance(self.workspace, str):
            self.workspace = Path(self.workspace)


class ExecutorBackend(ABC):
    """Abstract base class for code execution backends.

    All execution backends (local, Docker, remote) must implement
    this interface to be compatible with DSAgent.

    Example:
        class MyCustomExecutor(ExecutorBackend):
            def start(self) -> None:
                # Initialize your execution environment
                pass

            def execute(self, code: str) -> ExecutionResult:
                # Execute code and return results
                pass

            # ... implement other abstract methods
    """

    def __init__(self, config: Optional[ExecutorConfig] = None):
        """Initialize the executor.

        Args:
            config: Executor configuration
        """
        self.config = config or ExecutorConfig()
        self._started = False

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Check if the executor is running and ready for code execution."""
        pass

    @property
    def backend_name(self) -> str:
        """Return the name of this backend for logging/display."""
        return self.__class__.__name__

    @abstractmethod
    def start(self) -> None:
        """Start the execution environment.

        This should initialize the kernel/container/connection
        and prepare it for code execution.

        Raises:
            RuntimeError: If the executor fails to start
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Shutdown the execution environment.

        This should clean up all resources and stop any running
        kernels/containers/connections.
        """
        pass

    @abstractmethod
    def execute(self, code: str) -> ExecutionResult:
        """Execute code and return the result.

        Args:
            code: Python code to execute

        Returns:
            ExecutionResult containing stdout, stderr, errors, and images
        """
        pass

    @abstractmethod
    def get_kernel_state(self) -> KernelSnapshot:
        """Get the current state of the kernel.

        This includes defined variables, their types, DataFrame info,
        imported modules, etc.

        Returns:
            KernelSnapshot with current kernel state
        """
        pass

    def execute_silent(self, code: str) -> bool:
        """Execute code without capturing output.

        Useful for setup code that shouldn't pollute the output.

        Args:
            code: Python code to execute

        Returns:
            True if execution succeeded, False otherwise
        """
        result = self.execute(code)
        return result.success

    def reset(self) -> None:
        """Reset the kernel to a clean state.

        Default implementation restarts the kernel.
        Backends may override for more efficient reset.
        """
        self.shutdown()
        self.start()

    def is_healthy(self) -> bool:
        """Check if the executor is healthy and responsive.

        Default implementation tries to execute simple code.

        Returns:
            True if executor is healthy
        """
        if not self.is_running:
            return False
        try:
            result = self.execute("1 + 1")
            return result.success
        except Exception:
            return False

    def __enter__(self) -> "ExecutorBackend":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.shutdown()


class ExecutorError(Exception):
    """Base exception for executor errors."""
    pass


class ExecutorStartError(ExecutorError):
    """Raised when executor fails to start."""
    pass


class ExecutorTimeoutError(ExecutorError):
    """Raised when code execution times out."""
    pass


class ExecutorNotRunningError(ExecutorError):
    """Raised when trying to execute on a non-running executor."""
    pass
