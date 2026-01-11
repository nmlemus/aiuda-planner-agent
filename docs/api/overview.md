# Python API Overview

DSAgent provides a Python SDK for building data science applications and integrations.

## Agents

DSAgent offers two agent types for different use cases:

### ConversationalAgent

For interactive applications with multi-turn conversations:

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

# Multi-turn conversation with persistent context
response = agent.chat("Load the iris dataset")
response = agent.chat("Train a classifier on it")  # Has access to iris data
response = agent.chat("Show feature importance")   # Has access to trained model

agent.shutdown()
```

**Best for:**

- Chat interfaces
- Interactive notebooks
- Applications requiring context persistence
- Exploratory data analysis

[ConversationalAgent Reference →](conversational-agent.md)

### PlannerAgent

For one-shot tasks and automated pipelines:

```python
from dsagent import PlannerAgent

with PlannerAgent(model="gpt-4o", data="./data.csv") as agent:
    result = agent.run("Analyze this dataset and create visualizations")
    print(result.answer)
    print(f"Notebook: {result.notebook_path}")
```

**Best for:**

- Batch processing
- CI/CD pipelines
- Automated reports
- Single-task execution

[PlannerAgent Reference →](planner-agent.md)

## Quick Comparison

| Feature | ConversationalAgent | PlannerAgent |
|---------|---------------------|--------------|
| Multi-turn | ✅ | ❌ |
| Session persistence | ✅ | ❌ |
| Context manager | ❌ | ✅ |
| Streaming | ✅ | ❌ |
| Best for | Interactive | Batch |

## Installation

The Python API is included in the base package:

```bash
pip install datascience-agent
```

## Basic Usage

### ConversationalAgent

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

# Configure the agent
config = ConversationalAgentConfig(
    model="gpt-4o",
    workspace="./workspace",
    max_rounds=30,
    temperature=0.3,
)

# Create and start
agent = ConversationalAgent(config)
agent.start()

try:
    # Chat returns a response object
    response = agent.chat("Analyze the trends in sales.csv")

    print(response.content)      # Agent's text response
    print(response.code)         # Code that was executed (if any)
    print(response.artifacts)    # Generated files (charts, etc.)

finally:
    agent.shutdown()
```

### PlannerAgent

```python
from dsagent import PlannerAgent

# Using context manager (recommended)
with PlannerAgent(
    model="gpt-4o",
    data="./sales.csv",
    max_rounds=30,
) as agent:
    result = agent.run("Create a sales forecast for next quarter")

    print(result.answer)         # Final answer
    print(result.notebook_path)  # Path to generated notebook
    print(result.artifacts)      # Generated files
```

## Streaming Responses

ConversationalAgent supports streaming for real-time output:

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

# Stream responses
for chunk in agent.chat_stream("Explain the analysis step by step"):
    if chunk.type == "text":
        print(chunk.content, end="", flush=True)
    elif chunk.type == "code":
        print(f"\n```python\n{chunk.content}\n```")
    elif chunk.type == "result":
        print(f"\nResult: {chunk.content}")

agent.shutdown()
```

## Session Management

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

# Get current session ID
session_id = agent.session_id
print(f"Session: {session_id}")

# Later, resume the session
config = ConversationalAgentConfig(
    model="gpt-4o",
    session_id=session_id,  # Resume this session
)
agent = ConversationalAgent(config)
agent.start()

# Continue where you left off
response = agent.chat("What did we analyze earlier?")
```

## Error Handling

```python
from dsagent import PlannerAgent
from dsagent.exceptions import (
    DSAgentError,
    ExecutionError,
    ModelError,
    TimeoutError,
)

try:
    with PlannerAgent(model="gpt-4o") as agent:
        result = agent.run("Analyze data.csv")
except ExecutionError as e:
    print(f"Code execution failed: {e}")
except ModelError as e:
    print(f"LLM error: {e}")
except TimeoutError as e:
    print(f"Task timed out: {e}")
except DSAgentError as e:
    print(f"General error: {e}")
```

## Next Steps

- [ConversationalAgent Reference](conversational-agent.md)
- [PlannerAgent Reference](planner-agent.md)
- [Examples](../examples/data-analysis.md)
