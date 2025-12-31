# DSAgent

An AI-powered autonomous agent for data analysis with dynamic planning and persistent Jupyter kernel execution.

## Features

- **Dynamic Planning**: Agent creates and follows plans with [x]/[ ] step tracking
- **Persistent Execution**: Code runs in a Jupyter kernel with variable persistence
- **Multi-Provider LLM**: Supports OpenAI, Anthropic, Google, Ollama via LiteLLM
- **Notebook Generation**: Automatically generates clean, runnable Jupyter notebooks
- **Event Streaming**: Real-time events for UI integration
- **Comprehensive Logging**: Full execution logs for debugging and ML retraining
- **Session Management**: State persistence for multi-user scenarios

## Installation

Using pip:
```bash
pip install datascience-agent
```

With FastAPI support:
```bash
pip install "datascience-agent[api]"
```

Using uv (recommended):
```bash
uv pip install datascience-agent
uv pip install "datascience-agent[api]"  # with FastAPI
```

For development:
```bash
git clone https://github.com/nmlemus/dsagent
cd dsagent
uv sync --all-extras
```

## Quick Start

### Basic Usage

```python
from dsagent import PlannerAgent

# Create agent
with PlannerAgent(model="gpt-4o", workspace="./workspace") as agent:
    result = agent.run("Analyze sales_data.csv and identify top performing products")

    print(result.answer)
    print(f"Notebook: {result.notebook_path}")
```

### With Streaming

```python
from dsagent import PlannerAgent, EventType

agent = PlannerAgent(model="claude-3-sonnet-20240229")
agent.start()

for event in agent.run_stream("Build a predictive model for customer churn"):
    if event.type == EventType.PLAN_UPDATED:
        print(f"Plan: {event.plan.raw_text if event.plan else ''}")
    elif event.type == EventType.CODE_SUCCESS:
        print("Code executed successfully")
    elif event.type == EventType.CODE_FAILED:
        print("Code execution failed")
    elif event.type == EventType.ANSWER_ACCEPTED:
        print(f"Answer: {event.message}")

# Get result with notebook after streaming
result = agent.get_result()
print(f"Notebook: {result.notebook_path}")

agent.shutdown()
```

### FastAPI Integration

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from uuid import uuid4
from dsagent import PlannerAgent, EventType

app = FastAPI()

@app.post("/analyze")
async def analyze(task: str):
    async def event_stream():
        agent = PlannerAgent(
            model="gpt-4o",
            session_id=str(uuid4()),
        )
        agent.start()

        try:
            for event in agent.run_stream(task):
                yield f"data: {event.to_sse()}\n\n"
        finally:
            agent.shutdown()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

## Command Line Interface

The package includes a CLI for quick analysis from the terminal:

```bash
dsagent "Analyze this dataset and create visualizations" --data ./my_data.csv
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--data` | `-d` | Path to data file or directory (required) |
| `--model` | `-m` | LLM model to use (default: gpt-4o) |
| `--workspace` | `-w` | Output directory (default: ./workspace) |
| `--run-id` | | Custom run ID for this execution |
| `--max-rounds` | `-r` | Max iterations (default: 30) |
| `--quiet` | `-q` | Suppress verbose output |
| `--no-stream` | | Disable streaming output |

### CLI Examples

```bash
# Basic analysis
dsagent "Find trends and patterns" -d ./sales.csv

# With specific model
dsagent "Build ML model" -d ./dataset -m claude-3-sonnet-20240229

# Custom output directory
dsagent "Create charts" -d ./data -w ./output

# With custom run ID
dsagent "Analyze" -d ./data --run-id my-analysis-001

# Quiet mode
dsagent "Analyze" -d ./data -q
```

### Output Structure

Each run creates an isolated workspace:
```
workspace/
└── runs/
    └── {run_id}/
        ├── data/          # Input data (copied)
        ├── notebooks/     # Generated notebooks
        ├── artifacts/     # Images, charts, outputs
        └── logs/
            ├── run.log        # Human-readable log
            └── events.jsonl   # Structured events for ML
```

## Configuration

```python
from dsagent import PlannerAgent, RunContext

# With automatic run isolation
context = RunContext(workspace="./workspace")
agent = PlannerAgent(
    model="gpt-4o",           # Any LiteLLM-supported model
    context=context,          # Run context for isolation
    max_rounds=30,            # Max agent iterations
    max_tokens=4096,          # Max tokens per response
    temperature=0.2,          # LLM temperature
    timeout=300,              # Code execution timeout (seconds)
    verbose=True,             # Print to console
    event_callback=None,      # Callback for events
)
```

## Supported Models

Any model supported by [LiteLLM](https://docs.litellm.ai/docs/providers):

- OpenAI: `gpt-4o`, `gpt-4-turbo`, `gpt-3.5-turbo`
- Anthropic: `claude-3-opus-20240229`, `claude-3-sonnet-20240229`
- Google: `gemini-pro`, `gemini-1.5-pro`
- Ollama: `ollama/llama3`, `ollama/codellama`
- And many more...

## Event Types

```python
from dsagent import EventType

EventType.AGENT_STARTED       # Agent started processing
EventType.AGENT_FINISHED      # Agent finished
EventType.AGENT_ERROR         # Error occurred
EventType.ROUND_STARTED       # New iteration round
EventType.ROUND_FINISHED      # Round completed
EventType.LLM_CALL_STARTED    # LLM call started
EventType.LLM_CALL_FINISHED   # LLM response received
EventType.PLAN_CREATED        # Plan was created
EventType.PLAN_UPDATED        # Plan was updated
EventType.CODE_EXECUTING      # Code execution started
EventType.CODE_SUCCESS        # Code execution succeeded
EventType.CODE_FAILED         # Code execution failed
EventType.ANSWER_ACCEPTED     # Final answer generated
EventType.ANSWER_REJECTED     # Answer rejected (plan incomplete)
```

## Architecture

```
dsagent/
├── agents/
│   └── base.py          # PlannerAgent - main user interface
├── core/
│   ├── context.py       # RunContext - workspace management
│   ├── engine.py        # AgentEngine - main loop
│   ├── executor.py      # JupyterExecutor - code execution
│   └── planner.py       # PlanParser - response parsing
├── schema/
│   └── models.py        # Pydantic models
└── utils/
    ├── logger.py        # AgentLogger - console logging
    ├── run_logger.py    # RunLogger - comprehensive logging
    └── notebook.py      # NotebookBuilder - notebook generation
```

## License

MIT
