"""Tests for kernel management module."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dsagent.kernel.backend import (
    ExecutorBackend,
    ExecutorConfig,
    ExecutorError,
    ExecutorStartError,
    ExecutorNotRunningError,
)
from dsagent.kernel.introspector import (
    KernelIntrospector,
    IntrospectionResult,
    INTROSPECTION_CODE,
)
from dsagent.kernel.local import LocalExecutor
from dsagent.schema.models import ExecutionResult
from dsagent.session.models import KernelSnapshot


class TestExecutorConfig:
    """Tests for ExecutorConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ExecutorConfig()

        assert config.timeout == 300
        assert config.workspace == Path("./workspace")
        assert config.docker_image is None
        assert config.jupyter_url is None

    def test_custom_config(self, tmp_path):
        """Test custom configuration."""
        config = ExecutorConfig(
            workspace=tmp_path,
            timeout=600,
            memory_limit="4g",
            cpu_limit=2.0,
        )

        assert config.workspace == tmp_path
        assert config.timeout == 600
        assert config.memory_limit == "4g"
        assert config.cpu_limit == 2.0

    def test_string_workspace_conversion(self, tmp_path):
        """Test that string workspace is converted to Path."""
        config = ExecutorConfig(workspace=str(tmp_path))

        assert isinstance(config.workspace, Path)
        assert config.workspace == tmp_path


class TestIntrospectionResult:
    """Tests for IntrospectionResult."""

    def test_empty_result(self):
        """Test empty introspection result."""
        result = IntrospectionResult()

        assert result.success is True
        assert result.variables == {}
        assert result.dataframes == {}
        assert result.imports == []
        assert result.functions == []

    def test_to_kernel_snapshot(self):
        """Test conversion to KernelSnapshot."""
        result = IntrospectionResult(
            variables={"x": "int", "df": "DataFrame"},
            dataframes={"df": {"shape": [100, 5], "columns": ["a", "b"]}},
            imports=["pandas", "numpy"],
        )

        snapshot = result.to_kernel_snapshot()

        assert isinstance(snapshot, KernelSnapshot)
        assert snapshot.variables == result.variables
        assert snapshot.dataframes == result.dataframes
        assert snapshot.imports == result.imports

    def test_get_summary_empty(self):
        """Test summary for empty kernel."""
        result = IntrospectionResult()
        summary = result.get_summary()

        assert "empty" in summary.lower()

    def test_get_summary_with_data(self):
        """Test summary with variables and DataFrames."""
        result = IntrospectionResult(
            variables={"x": "int", "name": "str", "df": "DataFrame"},
            dataframes={"df": {"shape": [100, 3], "columns": ["a", "b", "c"]}},
            imports=["pandas"],
            functions=["my_func"],
        )

        summary = result.get_summary()

        assert "df" in summary
        assert "100" in summary
        assert "x" in summary
        assert "my_func" in summary


class TestKernelIntrospector:
    """Tests for KernelIntrospector."""

    def test_init_with_functions(self):
        """Test initialization with execute functions."""
        mock_execute = MagicMock(return_value=ExecutionResult())
        mock_silent = MagicMock(return_value=True)

        introspector = KernelIntrospector(
            execute_fn=mock_execute,
            silent_fn=mock_silent,
        )

        assert introspector._execute == mock_execute
        assert introspector._silent == mock_silent

    def test_introspect_success(self):
        """Test successful introspection."""
        mock_result = ExecutionResult(
            stdout='{"variables": {"x": "int"}, "dataframes": {}, '
                   '"imports": ["pandas"], "functions": [], "classes": []}',
            success=True
        )
        mock_execute = MagicMock(return_value=mock_result)
        mock_silent = MagicMock(return_value=True)

        introspector = KernelIntrospector(
            execute_fn=mock_execute,
            silent_fn=mock_silent,
        )

        result = introspector.introspect()

        assert result.success is True
        assert result.variables == {"x": "int"}
        assert result.imports == ["pandas"]

    def test_introspect_failure(self):
        """Test introspection with execution failure."""
        mock_result = ExecutionResult(
            error="Execution failed",
            success=False
        )
        mock_execute = MagicMock(return_value=mock_result)
        mock_silent = MagicMock(return_value=True)

        introspector = KernelIntrospector(
            execute_fn=mock_execute,
            silent_fn=mock_silent,
        )

        result = introspector.introspect()

        assert result.success is False
        assert result.error is not None

    def test_introspect_invalid_json(self):
        """Test introspection with invalid JSON output."""
        mock_result = ExecutionResult(
            stdout="not valid json",
            success=True
        )
        mock_execute = MagicMock(return_value=mock_result)
        mock_silent = MagicMock(return_value=True)

        introspector = KernelIntrospector(
            execute_fn=mock_execute,
            silent_fn=mock_silent,
        )

        result = introspector.introspect()

        assert result.success is False
        assert "parse" in result.error.lower()

    def test_get_variable_info(self):
        """Test getting variable info."""
        mock_result = ExecutionResult(
            stdout='{"type": "int"}',
            success=True
        )
        mock_execute = MagicMock(return_value=mock_result)
        mock_silent = MagicMock(return_value=True)

        introspector = KernelIntrospector(
            execute_fn=mock_execute,
            silent_fn=mock_silent,
        )

        info = introspector.get_variable_info("x")

        assert info is not None
        assert info["type"] == "int"

    def test_get_variable_info_not_found(self):
        """Test getting info for non-existent variable."""
        mock_result = ExecutionResult(
            stdout="null",
            success=True
        )
        mock_execute = MagicMock(return_value=mock_result)
        mock_silent = MagicMock(return_value=True)

        introspector = KernelIntrospector(
            execute_fn=mock_execute,
            silent_fn=mock_silent,
        )

        info = introspector.get_variable_info("nonexistent")

        assert info is None


class TestLocalExecutor:
    """Tests for LocalExecutor.

    Note: These tests require a working Jupyter kernel, so they
    are slower and may be skipped in some CI environments.
    """

    def test_init(self, tmp_path):
        """Test executor initialization."""
        config = ExecutorConfig(workspace=tmp_path)
        executor = LocalExecutor(config)

        assert executor.workspace == tmp_path
        assert executor.is_running is False

    def test_context_manager(self, tmp_path):
        """Test using executor as context manager."""
        config = ExecutorConfig(workspace=tmp_path, timeout=30)

        with LocalExecutor(config) as executor:
            assert executor.is_running is True
            result = executor.execute("x = 1 + 1")
            assert result.success is True

        assert executor.is_running is False

    def test_execute_simple(self, tmp_path):
        """Test simple code execution."""
        config = ExecutorConfig(workspace=tmp_path, timeout=30)

        with LocalExecutor(config) as executor:
            result = executor.execute("print('hello')")

            assert result.success is True
            assert "hello" in result.stdout

    def test_execute_with_output(self, tmp_path):
        """Test execution with expression output."""
        config = ExecutorConfig(workspace=tmp_path, timeout=30)

        with LocalExecutor(config) as executor:
            result = executor.execute("1 + 2")

            assert result.success is True
            assert "3" in result.stdout

    def test_execute_with_error(self, tmp_path):
        """Test execution with error."""
        config = ExecutorConfig(workspace=tmp_path, timeout=30)

        with LocalExecutor(config) as executor:
            result = executor.execute("1 / 0")

            assert result.success is False
            assert result.error is not None
            assert "ZeroDivision" in result.error

    def test_state_persistence(self, tmp_path):
        """Test that state persists between executions."""
        config = ExecutorConfig(workspace=tmp_path, timeout=30)

        with LocalExecutor(config) as executor:
            executor.execute("x = 42")
            result = executor.execute("print(x)")

            assert result.success is True
            assert "42" in result.stdout

    def test_import_persistence(self, tmp_path):
        """Test that imports persist between executions."""
        config = ExecutorConfig(workspace=tmp_path, timeout=30)

        with LocalExecutor(config) as executor:
            executor.execute("import math")
            result = executor.execute("print(math.pi)")

            assert result.success is True
            assert "3.14" in result.stdout

    def test_get_kernel_state(self, tmp_path):
        """Test getting kernel state."""
        config = ExecutorConfig(workspace=tmp_path, timeout=30)

        with LocalExecutor(config) as executor:
            executor.execute("x = 10")
            executor.execute("name = 'test'")

            state = executor.get_kernel_state()

            assert isinstance(state, KernelSnapshot)
            assert "x" in state.variables
            assert "name" in state.variables

    def test_get_kernel_state_with_dataframe(self, tmp_path):
        """Test getting kernel state with DataFrame."""
        config = ExecutorConfig(workspace=tmp_path, timeout=60)

        with LocalExecutor(config) as executor:
            executor.execute("import pandas as pd")
            executor.execute("df = pd.DataFrame({'a': [1,2,3], 'b': [4,5,6]})")

            state = executor.get_kernel_state()

            assert "df" in state.variables
            assert state.variables["df"] == "DataFrame"
            assert "df" in state.dataframes
            assert state.dataframes["df"]["shape"] == [3, 2]

    def test_get_variables(self, tmp_path):
        """Test getting variable list."""
        config = ExecutorConfig(workspace=tmp_path, timeout=30)

        with LocalExecutor(config) as executor:
            executor.execute("a = 1")
            executor.execute("b = 2")

            variables = executor.get_variables()

            assert "a" in variables
            assert "b" in variables

    def test_execute_silent(self, tmp_path):
        """Test silent execution."""
        config = ExecutorConfig(workspace=tmp_path, timeout=30)

        with LocalExecutor(config) as executor:
            success = executor.execute_silent("x = 100")

            assert success is True

            # Verify variable was set
            result = executor.execute("print(x)")
            assert "100" in result.stdout

    def test_is_healthy(self, tmp_path):
        """Test health check."""
        config = ExecutorConfig(workspace=tmp_path, timeout=30)

        with LocalExecutor(config) as executor:
            assert executor.is_healthy() is True

    def test_is_healthy_not_started(self, tmp_path):
        """Test health check when not started."""
        config = ExecutorConfig(workspace=tmp_path)
        executor = LocalExecutor(config)

        assert executor.is_healthy() is False

    def test_reset(self, tmp_path):
        """Test kernel reset."""
        config = ExecutorConfig(workspace=tmp_path, timeout=30)

        with LocalExecutor(config) as executor:
            executor.execute("my_var = 123")
            executor.reset()

            # Variable should be cleared
            result = executor.execute("print(my_var)")
            assert result.success is False  # NameError

    def test_workspace_is_working_dir(self, tmp_path):
        """Test that workspace is the kernel's working directory."""
        config = ExecutorConfig(workspace=tmp_path, timeout=30)

        with LocalExecutor(config) as executor:
            result = executor.execute("import os; print(os.getcwd())")

            assert result.success is True
            assert str(tmp_path) in result.stdout

    def test_execute_not_started_raises(self, tmp_path):
        """Test that execute raises when not started."""
        config = ExecutorConfig(workspace=tmp_path)
        executor = LocalExecutor(config)

        with pytest.raises(ExecutorNotRunningError):
            executor.execute("1 + 1")

    def test_matplotlib_backend_configured(self, tmp_path):
        """Test that matplotlib is configured for non-interactive use."""
        config = ExecutorConfig(workspace=tmp_path, timeout=60)

        with LocalExecutor(config) as executor:
            result = executor.execute(
                "import matplotlib; print(matplotlib.get_backend())"
            )

            assert result.success is True
            assert "agg" in result.stdout.lower()

    def test_custom_init_code(self, tmp_path):
        """Test custom initialization code."""
        config = ExecutorConfig(
            workspace=tmp_path,
            timeout=30,
            init_code="CUSTOM_VAR = 'initialized'"
        )

        with LocalExecutor(config) as executor:
            result = executor.execute("print(CUSTOM_VAR)")

            assert result.success is True
            assert "initialized" in result.stdout


class TestLocalExecutorIntegration:
    """Integration tests for LocalExecutor with real kernel operations."""

    def test_dataframe_operations(self, tmp_path):
        """Test DataFrame creation and manipulation."""
        config = ExecutorConfig(workspace=tmp_path, timeout=60)

        with LocalExecutor(config) as executor:
            # Create DataFrame
            executor.execute("import pandas as pd")
            executor.execute("""
df = pd.DataFrame({
    'name': ['Alice', 'Bob', 'Charlie'],
    'age': [25, 30, 35],
    'city': ['NYC', 'LA', 'Chicago']
})
            """)

            # Query DataFrame
            result = executor.execute("print(df.shape)")
            assert "(3, 3)" in result.stdout

            # Get kernel state
            state = executor.get_kernel_state()
            assert state.dataframes["df"]["shape"] == [3, 3]
            assert "name" in state.dataframes["df"]["columns"]

    def test_plot_generation(self, tmp_path):
        """Test that plots can be created and saved."""
        config = ExecutorConfig(workspace=tmp_path, timeout=60)

        with LocalExecutor(config) as executor:
            executor.execute("import matplotlib.pyplot as plt")
            # Create and save a plot
            result = executor.execute(f"""
fig, ax = plt.subplots()
ax.plot([1, 2, 3], [1, 4, 9])
fig.savefig('{tmp_path}/test_plot.png')
plt.close(fig)
print('Plot saved successfully')
            """)

            assert result.success is True
            assert "successfully" in result.stdout
            assert (tmp_path / "test_plot.png").exists()

    def test_sklearn_model(self, tmp_path):
        """Test sklearn model creation and fitting."""
        config = ExecutorConfig(workspace=tmp_path, timeout=120)

        with LocalExecutor(config) as executor:
            executor.execute("from sklearn.linear_model import LinearRegression")
            executor.execute("import numpy as np")
            executor.execute("""
X = np.array([[1], [2], [3], [4]])
y = np.array([2, 4, 6, 8])
model = LinearRegression()
model.fit(X, y)
            """)

            state = executor.get_kernel_state()

            assert "model" in state.variables
            assert "LinearRegression" in state.variables["model"]
            assert "fitted" in state.variables["model"]
