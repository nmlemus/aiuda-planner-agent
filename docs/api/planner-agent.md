# PlannerAgent

The `PlannerAgent` is designed for one-shot tasks and automated pipelines. It creates a plan, executes it, and returns structured results.

## Basic Usage

```python
from dsagent import PlannerAgent

with PlannerAgent(model="gpt-4o", data="./data.csv") as agent:
    result = agent.run("Analyze this dataset")
    print(result.answer)
```

## Constructor

```python
PlannerAgent(
    model: str = "gpt-4o",
    data: Optional[str] = None,
    workspace: str = "./workspace",
    max_rounds: int = 30,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    code_timeout: int = 300,
    hitl_mode: str = "none",
    mcp_config: Optional[str] = None,
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | `str` | `"gpt-4o"` | LLM model to use |
| `data` | `str \| None` | `None` | Path to input data file |
| `workspace` | `str` | `"./workspace"` | Output directory |
| `max_rounds` | `int` | `30` | Maximum execution rounds |
| `temperature` | `float` | `0.3` | LLM temperature |
| `max_tokens` | `int` | `4096` | Max tokens per response |
| `code_timeout` | `int` | `300` | Code execution timeout (seconds) |
| `hitl_mode` | `str` | `"none"` | Human-in-the-loop mode |
| `mcp_config` | `str \| None` | `None` | Path to MCP config file |

## Methods

### run()

Execute a task and return results.

```python
result = agent.run(task: str) -> AgentResult
```

**Parameters:**

- `task` (str): The task description

**Returns:** `AgentResult` object

### AgentResult

```python
@dataclass
class AgentResult:
    answer: str              # Final answer text
    notebook_path: str       # Path to generated notebook
    artifacts: List[str]     # List of generated files
    plan: Optional[Plan]     # Execution plan
    execution_log: List[dict]  # Detailed execution log
    success: bool            # Whether task completed successfully
    error: Optional[str]     # Error message if failed
```

## Examples

### Basic Analysis

```python
from dsagent import PlannerAgent

with PlannerAgent(model="gpt-4o") as agent:
    result = agent.run("Create a visualization of global temperature trends")

    print(f"Answer: {result.answer}")
    print(f"Notebook: {result.notebook_path}")
    print(f"Charts: {result.artifacts}")
```

### With Input Data

```python
from dsagent import PlannerAgent

with PlannerAgent(
    model="gpt-4o",
    data="./sales_2024.csv",
    workspace="./output",
) as agent:
    result = agent.run("""
        Analyze sales trends and create:
        1. Monthly revenue chart
        2. Top 10 products by sales
        3. Regional performance comparison
    """)

    for artifact in result.artifacts:
        print(f"Generated: {artifact}")
```

### Human-in-the-Loop

```python
from dsagent import PlannerAgent

with PlannerAgent(
    model="gpt-4o",
    hitl_mode="plan",  # Approve plan before execution
) as agent:
    result = agent.run("Build a predictive model for customer churn")
    # Agent will pause and ask for plan approval
```

### With MCP Tools

```python
from dsagent import PlannerAgent

with PlannerAgent(
    model="gpt-4o",
    mcp_config="~/.dsagent/mcp.yaml",
) as agent:
    result = agent.run("Search for latest AI research and summarize findings")
```

### Error Handling

```python
from dsagent import PlannerAgent
from dsagent.exceptions import ExecutionError, TimeoutError

try:
    with PlannerAgent(model="gpt-4o", code_timeout=60) as agent:
        result = agent.run("Train a large neural network")

        if not result.success:
            print(f"Task failed: {result.error}")
        else:
            print(f"Completed: {result.answer}")

except TimeoutError:
    print("Task exceeded time limit")
except ExecutionError as e:
    print(f"Execution error: {e}")
```

### Batch Processing

```python
from dsagent import PlannerAgent
from pathlib import Path

data_files = Path("./data").glob("*.csv")

for data_file in data_files:
    with PlannerAgent(model="gpt-4o", data=str(data_file)) as agent:
        result = agent.run("Generate summary statistics and key insights")

        output_dir = Path("./reports") / data_file.stem
        output_dir.mkdir(parents=True, exist_ok=True)

        # Move artifacts to organized location
        for artifact in result.artifacts:
            # Process artifacts...
            pass
```

## Output Structure

Each run creates organized output in the workspace:

```
workspace/runs/{run_id}/
├── data/
│   └── input.csv           # Copy of input data
├── notebooks/
│   └── analysis.ipynb      # Generated notebook
├── artifacts/
│   ├── chart_1.png
│   ├── chart_2.png
│   └── model.pkl
└── logs/
    └── execution.log
```

## See Also

- [ConversationalAgent](conversational-agent.md) - For interactive sessions
- [API Overview](overview.md) - General API concepts
- [Examples](../examples/data-analysis.md) - More usage examples
