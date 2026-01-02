# DSAgent

[![Upload Python Package](https://github.com/nmlemus/dsagent/actions/workflows/python-publish.yml/badge.svg)](https://github.com/nmlemus/dsagent/actions/workflows/python-publish.yml)
[![PyPI](https://img.shields.io/pypi/v/datascience-agent)](https://pypi.org/project/datascience-agent/)
[![Python](https://img.shields.io/pypi/pyversions/datascience-agent)](https://pypi.org/project/datascience-agent/)
[![License](https://img.shields.io/github/license/nmlemus/dsagent)](https://github.com/nmlemus/dsagent/blob/main/LICENSE)

An AI-powered autonomous agent for data analysis with dynamic planning and persistent Jupyter kernel execution.

## Features

- **Dynamic Planning**: Agent creates and follows plans with [x]/[ ] step tracking
- **Persistent Execution**: Code runs in a Jupyter kernel with variable persistence
- **Multi-Provider LLM**: Supports OpenAI, Anthropic, Google, Ollama via LiteLLM
- **Notebook Generation**: Automatically generates clean, runnable Jupyter notebooks
- **Event Streaming**: Real-time events for UI integration
- **Comprehensive Logging**: Full execution logs for debugging and ML retraining
- **Session Management**: State persistence for multi-user scenarios
- **Human-in-the-Loop**: Configurable checkpoints for human approval and feedback
- **MCP Tools Support**: Connect to external tools via Model Context Protocol (web search, databases, etc.)

## Installation

Using pip:
```bash
pip install datascience-agent
```

With FastAPI support:
```bash
pip install "datascience-agent[api]"
```

With MCP tools support:
```bash
pip install "datascience-agent[mcp]"
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

## Configuration

### API Keys

DSAgent requires an API key for your chosen LLM provider. Set it via environment variable or `.env` file:

**Option 1: Environment variable**
```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic (Claude)
export ANTHROPIC_API_KEY="sk-ant-..."

# Google (Gemini)
export GOOGLE_API_KEY="..."
```

**Option 2: .env file**

Copy the example and fill in your values:
```bash
cp .env.example .env
# Edit .env with your API keys
```

The `.env` file is searched in this order:
1. Current working directory
2. Project root
3. `~/.dsagent/.env`

**Priority order:** CLI arguments > Environment variables > `.env` file > defaults

See [.env.example](.env.example) for all available configuration options.

## Quick Start

### Basic Usage

```python
from dsagent import PlannerAgent

# Basic usage - task only
with PlannerAgent(model="gpt-4o") as agent:
    result = agent.run("Write a function to calculate fibonacci numbers")
    print(result.answer)

# With data file - automatically copied to workspace/data/
with PlannerAgent(model="gpt-4o", data="./sales_data.csv") as agent:
    result = agent.run("Analyze this dataset and identify top performing products")
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
# With data file
dsagent "Analyze this dataset and create visualizations" --data ./my_data.csv

# Without data (code generation, research, etc.)
dsagent "Write a Python script to scrape weather data" --model claude-3-5-sonnet-20241022
```

### CLI Options

| Option | Short | Description |
|--------|-------|-------------|
| `--data` | `-d` | Path to data file or directory (optional) |
| `--model` | `-m` | LLM model to use (default: gpt-4o) |
| `--workspace` | `-w` | Output directory (default: ./workspace) |
| `--run-id` | | Custom run ID for this execution |
| `--max-rounds` | `-r` | Max iterations (default: 30) |
| `--quiet` | `-q` | Suppress verbose output |
| `--no-stream` | | Disable streaming output |
| `--hitl` | | HITL mode: none, plan_only, on_error, plan_and_answer, full |
| `--mcp-config` | | Path to MCP servers YAML configuration file |

### CLI Examples

```bash
# Basic analysis with data
dsagent "Find trends and patterns" -d ./sales.csv

# Code generation (no data needed)
dsagent "Write a REST API client for GitHub" --model gpt-4o

# With specific model
dsagent "Build ML model" -d ./dataset -m claude-3-sonnet-20240229

# Custom output directory
dsagent "Create charts" -d ./data -w ./output

# With MCP tools (no data)
dsagent "Search for Python best practices and summarize" --mcp-config ~/.dsagent/mcp.yaml

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

## Agent Configuration

```python
from dsagent import PlannerAgent, RunContext

# Simple usage
agent = PlannerAgent(
    model="gpt-4o",           # Any LiteLLM-supported model
    data="./my_data.csv",     # Optional: data file or directory
    workspace="./workspace",  # Working directory
    max_rounds=30,            # Max agent iterations
    max_tokens=4096,          # Max tokens per response
    temperature=0.2,          # LLM temperature
    timeout=300,              # Code execution timeout (seconds)
    verbose=True,             # Print to console
    event_callback=None,      # Callback for events
)

# With run isolation (for multi-user scenarios)
context = RunContext(workspace="./workspace")
context.copy_data("./dataset")  # Copy data to run's data folder
agent = PlannerAgent(model="gpt-4o", context=context)
```

### Workspace Structure

When running, DSAgent creates this structure:
```
workspace/
├── data/          # Input data (read from here)
├── artifacts/     # Outputs: images, models, CSVs, reports
├── notebooks/     # Generated Jupyter notebooks
└── logs/          # Execution logs
```

With `RunContext`, each run gets isolated storage under `workspace/runs/{run_id}/`.

## Human-in-the-Loop (HITL)

Control agent autonomy with configurable HITL modes:

```python
from dsagent import PlannerAgent, HITLMode, EventType

# Create agent with HITL enabled
agent = PlannerAgent(
    model="gpt-4o",
    hitl=HITLMode.PLAN_ONLY,  # Pause for plan approval
)
agent.start()

# Run with streaming to handle HITL events
for event in agent.run_stream("Analyze sales data"):
    if event.type == EventType.HITL_AWAITING_PLAN_APPROVAL:
        print(f"Plan proposed:\n{event.plan.raw_text}")
        # Approve the plan
        agent.approve()
        # Or reject: agent.reject("Bad plan")
        # Or modify: agent.modify_plan("1. [ ] Better step")

    elif event.type == EventType.ANSWER_ACCEPTED:
        print(f"Answer: {event.message}")

agent.shutdown()
```

### HITL Modes

| Mode | Description |
|------|-------------|
| `HITLMode.NONE` | Fully autonomous (default) |
| `HITLMode.PLAN_ONLY` | Pause after plan generation for approval |
| `HITLMode.ON_ERROR` | Pause when code execution fails |
| `HITLMode.PLAN_AND_ANSWER` | Pause on plan + before final answer |
| `HITLMode.FULL` | Pause before every code execution |

### HITL Actions

```python
# Approve current pending item
agent.approve("Looks good!")

# Reject and abort
agent.reject("This approach won't work")

# Modify the plan
agent.modify_plan("1. [ ] New step\n2. [ ] Another step")

# Modify code before execution (FULL mode)
agent.modify_code("import pandas as pd\ndf = pd.read_csv('data.csv')")

# Skip current step
agent.skip()

# Send feedback to guide the agent
agent.send_feedback("Try using a different algorithm")
```

### HITL Events

```python
EventType.HITL_AWAITING_PLAN_APPROVAL    # Waiting for plan approval
EventType.HITL_AWAITING_CODE_APPROVAL    # Waiting for code approval (FULL mode)
EventType.HITL_AWAITING_ERROR_GUIDANCE   # Waiting for error guidance
EventType.HITL_AWAITING_ANSWER_APPROVAL  # Waiting for answer approval
EventType.HITL_FEEDBACK_RECEIVED         # Human feedback was received
EventType.HITL_PLAN_APPROVED             # Plan was approved
EventType.HITL_PLAN_MODIFIED             # Plan was modified
EventType.HITL_PLAN_REJECTED             # Plan was rejected
EventType.HITL_EXECUTION_ABORTED         # Execution was aborted
```

## MCP Tools Support

DSAgent supports the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) to connect to external tool servers, enabling capabilities like web search, database queries, and more.

### Installation

```bash
pip install "datascience-agent[mcp]"
```

### Configuration

Create a YAML configuration file (e.g., `~/.dsagent/mcp.yaml`):

```yaml
servers:
  # Brave Search - web search capability
  - name: brave_search
    transport: stdio
    command: ["npx", "-y", "@modelcontextprotocol/server-brave-search"]
    env:
      BRAVE_API_KEY: "${BRAVE_API_KEY}"

  # Filesystem access
  - name: filesystem
    transport: stdio
    command: ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]

  # HTTP-based MCP server
  - name: custom_server
    transport: http
    url: "http://localhost:8080/mcp"
    enabled: false  # Disable without removing
```

### Usage

#### Python API

```python
from dsagent import PlannerAgent

agent = PlannerAgent(
    model="gpt-4o",
    mcp_config="~/.dsagent/mcp.yaml",  # Path to config
)
agent.start()

# Agent can now use web search and other MCP tools
for event in agent.run_stream("Search for latest AI trends and analyze them"):
    if event.type == EventType.ANSWER_ACCEPTED:
        print(event.message)

agent.shutdown()
```

#### CLI

```bash
# Set API keys
export BRAVE_API_KEY="your-brave-api-key"

# Run with MCP tools (no data needed for web search)
dsagent "Search for Python best practices and summarize" \
  --mcp-config ~/.dsagent/mcp.yaml

# With data
dsagent "Search for similar datasets online and compare with mine" \
  --data ./my_data.csv \
  --mcp-config ~/.dsagent/mcp.yaml
```

### Environment Variables

Use `${VAR_NAME}` syntax in YAML to reference environment variables:

```yaml
env:
  API_KEY: "${MY_API_KEY}"      # Resolved from environment
  STATIC_VALUE: "hardcoded"     # Static value
```

### Available MCP Servers

Some popular MCP servers you can use:

| Server | Package | Description |
|--------|---------|-------------|
| Brave Search | `@modelcontextprotocol/server-brave-search` | Web search via Brave API |
| Filesystem | `@modelcontextprotocol/server-filesystem` | File system access |
| PostgreSQL | `@modelcontextprotocol/server-postgres` | PostgreSQL database queries |
| Puppeteer | `@modelcontextprotocol/server-puppeteer` | Browser automation |

See [MCP Servers Directory](https://github.com/modelcontextprotocol/servers) for more options.

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
│   ├── hitl.py          # HITLGateway - human-in-the-loop
│   └── planner.py       # PlanParser - response parsing
├── tools/
│   ├── config.py        # MCP configuration models
│   └── mcp_manager.py   # MCPManager - MCP server connections
├── schema/
│   └── models.py        # Pydantic models
└── utils/
    ├── logger.py        # AgentLogger - console logging
    ├── run_logger.py    # RunLogger - comprehensive logging
    └── notebook.py      # NotebookBuilder - notebook generation
```

## License

MIT
