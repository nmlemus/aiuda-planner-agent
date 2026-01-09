"""Kernel introspection utilities.

This module provides tools for inspecting the state of a running kernel,
including variables, DataFrames, imports, and function definitions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from dsagent.schema.models import ExecutionResult
from dsagent.session.models import KernelSnapshot

if TYPE_CHECKING:
    from dsagent.kernel.backend import ExecutorBackend


# Introspection code to execute in the kernel
INTROSPECTION_CODE = '''
import json as _json
import sys as _sys

def _dsagent_introspect():
    """Gather kernel state information."""
    result = {
        "variables": {},
        "dataframes": {},
        "imports": [],
        "functions": [],
        "classes": [],
    }

    # Get all user-defined variables (exclude builtins and private)
    _skip = {
        '_json', '_sys', '_dsagent_introspect', '_skip', '_name', '_obj',
        '_result', 'In', 'Out', 'get_ipython', 'exit', 'quit', 'open',
        '_ih', '_oh', '_dh', '__', '___', '__builtin__', '__builtins__',
        '__doc__', '__loader__', '__name__', '__package__', '__spec__',
    }

    for _name, _obj in list(globals().items()):
        if _name.startswith('_') or _name in _skip:
            continue

        _type_name = type(_obj).__name__

        # Check if it's a DataFrame
        if _type_name == 'DataFrame':
            result["variables"][_name] = "DataFrame"
            try:
                result["dataframes"][_name] = {
                    "shape": list(_obj.shape),
                    "columns": list(_obj.columns)[:50],  # Limit columns
                    "dtypes": {str(k): str(v) for k, v in _obj.dtypes.items()},
                    "memory_mb": round(_obj.memory_usage(deep=True).sum() / 1024 / 1024, 2),
                }
            except Exception:
                result["dataframes"][_name] = {"shape": [0, 0], "columns": []}

        # Check if it's a Series
        elif _type_name == 'Series':
            result["variables"][_name] = f"Series[{len(_obj)}]"

        # Check if it's a function
        elif callable(_obj) and not isinstance(_obj, type):
            if hasattr(_obj, '__module__') and _obj.__module__ == '__main__':
                result["functions"].append(_name)
            else:
                result["variables"][_name] = f"function"

        # Check if it's a class
        elif isinstance(_obj, type):
            if hasattr(_obj, '__module__') and _obj.__module__ == '__main__':
                result["classes"].append(_name)
            else:
                result["variables"][_name] = "class"

        # Check if it's a model (sklearn, etc.)
        elif hasattr(_obj, 'fit') and hasattr(_obj, 'predict'):
            _model_type = _type_name
            if hasattr(_obj, 'classes_'):  # Fitted classifier
                _model_type += " (fitted)"
            elif hasattr(_obj, 'coef_'):  # Fitted regressor
                _model_type += " (fitted)"
            result["variables"][_name] = _model_type

        # Check if it's a numpy array
        elif _type_name == 'ndarray':
            try:
                result["variables"][_name] = f"ndarray{_obj.shape}"
            except Exception:
                result["variables"][_name] = "ndarray"

        # Check common types
        elif _type_name in ('int', 'float', 'str', 'bool', 'NoneType'):
            result["variables"][_name] = _type_name

        elif _type_name in ('list', 'tuple', 'set', 'frozenset'):
            try:
                result["variables"][_name] = f"{_type_name}[{len(_obj)}]"
            except Exception:
                result["variables"][_name] = _type_name

        elif _type_name == 'dict':
            try:
                result["variables"][_name] = f"dict[{len(_obj)}]"
            except Exception:
                result["variables"][_name] = "dict"

        else:
            result["variables"][_name] = _type_name

    # Get imported modules
    for _name, _obj in list(globals().items()):
        if _name.startswith('_') or _name in _skip:
            continue
        if isinstance(_obj, type(_sys)):  # It's a module
            result["imports"].append(_name)

    return result

# Execute and print as JSON
print(_json.dumps(_dsagent_introspect()))
'''

# Cleanup code to remove introspection artifacts
CLEANUP_CODE = '''
try:
    del _dsagent_introspect
except NameError:
    pass
'''


@dataclass
class IntrospectionResult:
    """Result of kernel introspection."""

    variables: Dict[str, str] = field(default_factory=dict)
    dataframes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    imports: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None

    def to_kernel_snapshot(self) -> KernelSnapshot:
        """Convert to KernelSnapshot for storage."""
        return KernelSnapshot(
            variables=self.variables,
            dataframes=self.dataframes,
            imports=self.imports,
        )

    def get_summary(self, max_items: int = 10) -> str:
        """Get a human-readable summary of kernel state."""
        lines = []

        if self.dataframes:
            lines.append("DataFrames:")
            for name, info in list(self.dataframes.items())[:max_items]:
                shape = info.get("shape", [0, 0])
                cols = info.get("columns", [])[:5]
                cols_str = ", ".join(cols)
                if len(info.get("columns", [])) > 5:
                    cols_str += f" (+{len(info['columns']) - 5} more)"
                lines.append(f"  {name}: {shape[0]} rows x {shape[1]} cols [{cols_str}]")

        other_vars = {k: v for k, v in self.variables.items()
                      if k not in self.dataframes}
        if other_vars:
            lines.append("\nVariables:")
            for name, type_name in list(other_vars.items())[:max_items]:
                lines.append(f"  {name}: {type_name}")
            if len(other_vars) > max_items:
                lines.append(f"  ... and {len(other_vars) - max_items} more")

        if self.functions:
            lines.append(f"\nFunctions: {', '.join(self.functions[:max_items])}")

        if self.imports:
            lines.append(f"\nImports: {', '.join(self.imports[:max_items])}")
            if len(self.imports) > max_items:
                lines.append(f"  ... and {len(self.imports) - max_items} more")

        return "\n".join(lines) if lines else "Kernel is empty"


class KernelIntrospector:
    """Introspects kernel state to provide context for LLM.

    This class executes special introspection code in the kernel
    to gather information about defined variables, DataFrames,
    imports, and functions.

    Example:
        introspector = KernelIntrospector(executor)
        result = introspector.introspect()
        print(result.get_summary())
    """

    def __init__(
        self,
        execute_fn: Callable[[str], ExecutionResult],
        silent_fn: Optional[Callable[[str], bool]] = None,
    ):
        """Initialize the introspector.

        Args:
            execute_fn: Function to execute code in the kernel
            silent_fn: Optional function to execute code silently
        """
        self._execute = execute_fn
        self._silent = silent_fn or (lambda code: execute_fn(code).success)

    @classmethod
    def from_executor(cls, executor: "ExecutorBackend") -> "KernelIntrospector":
        """Create an introspector from an executor backend.

        Args:
            executor: The executor backend to introspect

        Returns:
            KernelIntrospector instance
        """
        return cls(
            execute_fn=executor.execute,
            silent_fn=executor.execute_silent,
        )

    def introspect(self) -> IntrospectionResult:
        """Introspect the kernel state.

        Returns:
            IntrospectionResult with kernel state information
        """
        result = IntrospectionResult()

        try:
            # Execute introspection code
            exec_result = self._execute(INTROSPECTION_CODE)

            if not exec_result.success:
                result.success = False
                result.error = exec_result.error or "Introspection failed"
                return result

            # Parse JSON output
            output = exec_result.stdout.strip()
            if not output:
                result.success = False
                result.error = "No output from introspection"
                return result

            try:
                data = json.loads(output)
                result.variables = data.get("variables", {})
                result.dataframes = data.get("dataframes", {})
                result.imports = data.get("imports", [])
                result.functions = data.get("functions", [])
                result.classes = data.get("classes", [])
            except json.JSONDecodeError as e:
                result.success = False
                result.error = f"Failed to parse introspection: {e}"

        except Exception as e:
            result.success = False
            result.error = str(e)

        finally:
            # Clean up introspection artifacts
            self._silent(CLEANUP_CODE)

        return result

    def get_variable_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed info about a specific variable.

        Args:
            name: Variable name

        Returns:
            Dict with variable info or None if not found
        """
        code = f'''
import json as _json

_var = globals().get("{name}")
if _var is not None:
    _info = {{"type": type(_var).__name__}}

    # DataFrame details
    if hasattr(_var, 'shape') and hasattr(_var, 'columns'):
        _info["shape"] = list(_var.shape)
        _info["columns"] = list(_var.columns)
        _info["dtypes"] = {{str(k): str(v) for k, v in _var.dtypes.items()}}
        _info["head"] = _var.head(5).to_dict('records')

    # Array details
    elif hasattr(_var, 'shape') and hasattr(_var, 'dtype'):
        _info["shape"] = list(_var.shape)
        _info["dtype"] = str(_var.dtype)

    # Collection details
    elif isinstance(_var, (list, tuple, set, dict)):
        _info["length"] = len(_var)
        if isinstance(_var, dict):
            _info["keys"] = list(_var.keys())[:20]

    # Model details
    elif hasattr(_var, 'fit') and hasattr(_var, 'predict'):
        _info["is_fitted"] = hasattr(_var, 'classes_') or hasattr(_var, 'coef_')
        if hasattr(_var, 'feature_names_in_'):
            _info["features"] = list(_var.feature_names_in_)

    print(_json.dumps(_info))
else:
    print("null")
'''
        result = self._execute(code)
        self._silent("del _var, _info")

        if result.success and result.stdout.strip():
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                pass
        return None

    def get_dataframe_sample(
        self,
        name: str,
        n: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """Get sample rows from a DataFrame.

        Args:
            name: DataFrame variable name
            n: Number of rows to sample

        Returns:
            List of row dicts or None
        """
        code = f'''
import json as _json
_df = globals().get("{name}")
if _df is not None and hasattr(_df, 'head'):
    print(_json.dumps(_df.head({n}).to_dict('records')))
else:
    print("null")
'''
        result = self._execute(code)
        self._silent("del _df")

        if result.success and result.stdout.strip():
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                pass
        return None

    def get_dataframe_describe(self, name: str) -> Optional[Dict[str, Any]]:
        """Get statistical description of a DataFrame.

        Args:
            name: DataFrame variable name

        Returns:
            Dict with describe() output or None
        """
        code = f'''
import json as _json
_df = globals().get("{name}")
if _df is not None and hasattr(_df, 'describe'):
    print(_json.dumps(_df.describe().to_dict()))
else:
    print("null")
'''
        result = self._execute(code)
        self._silent("del _df")

        if result.success and result.stdout.strip():
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                pass
        return None
