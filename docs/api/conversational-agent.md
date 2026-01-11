# ConversationalAgent

The `ConversationalAgent` is designed for interactive, multi-turn conversations with persistent context and session management.

## Basic Usage

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

response = agent.chat("Hello, analyze my data")
print(response.content)

agent.shutdown()
```

## Configuration

```python
from dsagent import ConversationalAgentConfig

config = ConversationalAgentConfig(
    model: str = "gpt-4o",
    workspace: str = "./workspace",
    session_id: Optional[str] = None,
    max_rounds: int = 30,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    code_timeout: int = 300,
    hitl_mode: str = "none",
    mcp_config: Optional[str] = None,
    auto_summarize: bool = True,
    summarize_threshold: int = 20,
)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | `str` | `"gpt-4o"` | LLM model to use |
| `workspace` | `str` | `"./workspace"` | Output directory |
| `session_id` | `str \| None` | `None` | Resume existing session |
| `max_rounds` | `int` | `30` | Max rounds per message |
| `temperature` | `float` | `0.3` | LLM temperature |
| `max_tokens` | `int` | `4096` | Max tokens per response |
| `code_timeout` | `int` | `300` | Code timeout (seconds) |
| `hitl_mode` | `str` | `"none"` | Human-in-the-loop mode |
| `mcp_config` | `str \| None` | `None` | Path to MCP config |
| `auto_summarize` | `bool` | `True` | Auto-summarize long conversations |
| `summarize_threshold` | `int` | `20` | Messages before summarization |

## Methods

### start()

Initialize the agent and start a session.

```python
agent.start() -> None
```

### chat()

Send a message and get a response.

```python
response = agent.chat(message: str) -> ChatResponse
```

**Parameters:**

- `message` (str): User message

**Returns:** `ChatResponse` object

### chat_stream()

Send a message and stream the response.

```python
for chunk in agent.chat_stream(message: str) -> Iterator[StreamChunk]:
    print(chunk.content)
```

### shutdown()

Clean up resources and save session.

```python
agent.shutdown() -> None
```

### export_notebook()

Export session to Jupyter notebook.

```python
path = agent.export_notebook(filename: str) -> str
```

## Response Objects

### ChatResponse

```python
@dataclass
class ChatResponse:
    content: str              # Agent's text response
    code: Optional[str]       # Executed code (if any)
    execution_result: Optional[str]  # Code output
    artifacts: List[str]      # Generated files
    plan: Optional[Plan]      # Current plan state
```

### StreamChunk

```python
@dataclass
class StreamChunk:
    type: str       # "text", "code", "result", "artifact", "plan"
    content: str    # Chunk content
```

## Examples

### Multi-Turn Conversation

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

# First message
response = agent.chat("Load the iris dataset from sklearn")
print(response.content)

# Follow-up (has access to loaded data)
response = agent.chat("What are the feature names?")
print(response.content)

# Continue analysis
response = agent.chat("Train a random forest classifier")
print(response.content)

# Check results
response = agent.chat("What's the accuracy?")
print(response.content)

agent.shutdown()
```

### Streaming Responses

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

print("Agent: ", end="")
for chunk in agent.chat_stream("Explain linear regression step by step"):
    if chunk.type == "text":
        print(chunk.content, end="", flush=True)
    elif chunk.type == "code":
        print(f"\n\n```python\n{chunk.content}\n```\n")
    elif chunk.type == "result":
        print(f"\nOutput: {chunk.content}\n")

print()  # Newline at end
agent.shutdown()
```

### Session Persistence

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

# Start a new session
config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

response = agent.chat("Load sales.csv and calculate totals")
session_id = agent.session_id  # Save this
print(f"Session ID: {session_id}")

agent.shutdown()

# Later, resume the session
config = ConversationalAgentConfig(
    model="gpt-4o",
    session_id=session_id,
)
agent = ConversationalAgent(config)
agent.start()

# Variables from previous session are available
response = agent.chat("Show me the totals we calculated")
print(response.content)

agent.shutdown()
```

### Export to Notebook

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(model="gpt-4o")
agent = ConversationalAgent(config)
agent.start()

agent.chat("Create a scatter plot of random data")
agent.chat("Add a trend line")
agent.chat("Customize the colors")

# Export all code to notebook
notebook_path = agent.export_notebook("my_visualization.ipynb")
print(f"Saved to: {notebook_path}")

agent.shutdown()
```

### With Human-in-the-Loop

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

config = ConversationalAgentConfig(
    model="gpt-4o",
    hitl_mode="plan",  # Require plan approval
)
agent = ConversationalAgent(config)
agent.start()

# Agent will present plan and wait for approval
response = agent.chat("Build a machine learning pipeline")

# Response includes plan for review
if response.plan:
    print("Proposed plan:")
    for step in response.plan.steps:
        print(f"  - {step}")

# Approve or modify...
response = agent.chat("/approve")  # or provide feedback

agent.shutdown()
```

### Building a Chat Interface

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

def run_chat():
    config = ConversationalAgentConfig(model="gpt-4o")
    agent = ConversationalAgent(config)
    agent.start()

    print("DSAgent Chat (type 'quit' to exit)")
    print("-" * 40)

    try:
        while True:
            user_input = input("\nYou: ").strip()

            if user_input.lower() in ('quit', 'exit'):
                break

            if not user_input:
                continue

            print("\nAgent: ", end="")
            for chunk in agent.chat_stream(user_input):
                if chunk.type == "text":
                    print(chunk.content, end="", flush=True)
            print()

    finally:
        agent.shutdown()
        print("\nGoodbye!")

if __name__ == "__main__":
    run_chat()
```

## Properties

| Property | Type | Description |
|----------|------|-------------|
| `session_id` | `str` | Current session identifier |
| `message_count` | `int` | Number of messages in session |
| `kernel_variables` | `List[str]` | Variables in Jupyter kernel |

## See Also

- [PlannerAgent](planner-agent.md) - For one-shot tasks
- [API Overview](overview.md) - General API concepts
- [Examples](../examples/data-analysis.md) - More usage examples
