"""Kernel management for DSAgent.

This module provides abstractions for code execution backends,
allowing easy swapping between local Jupyter kernels, Docker containers,
or remote Jupyter servers.
"""

from dsagent.kernel.backend import ExecutorBackend, ExecutorConfig
from dsagent.kernel.introspector import KernelIntrospector, IntrospectionResult
from dsagent.kernel.local import LocalExecutor

__all__ = [
    "ExecutorBackend",
    "ExecutorConfig",
    "KernelIntrospector",
    "IntrospectionResult",
    "LocalExecutor",
]
