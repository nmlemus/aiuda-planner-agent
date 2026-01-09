# Python API Reference

DSAgent provides two main agents for different use cases:

- **ConversationalAgent**: For interactive chat applications with persistent context
- **PlannerAgent**: For one-shot tasks and automated pipelines

## ConversationalAgent

The `ConversationalAgent` is designed for building interactive chat interfaces where context persists across multiple messages.

### Basic Usage

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig

# Create configuration
config = ConversationalAgentConfig(model="gpt-4o")

# Create and start agent
agent = ConversationalAgent(config)
agent.start()

# Chat with persistent context
response = agent.chat("Load the iris dataset and show the first few rows")
print(response.content)

response = agent.chat("Now train a random forest classifier on it")
print(response.content)  # Has access to the iris dataset from previous message

# Clean up
agent.shutdown()
```

### ConversationalAgentConfig

```python
from dsagent import ConversationalAgentConfig
from dsagent.schema.models import HITLMode
from pathlib import Path

config = ConversationalAgentConfig(
    # LLM settings
    model="gpt-4o",              # LLM model to use
    max_tokens=4096,             # Max tokens per response
    temperature=0.2,             # LLM temperature

    # Workspace
    workspace=Path("./workspace"),  # Working directory

    # Human-in-the-loop
    hitl_mode=HITLMode.NONE,     # HITL mode (see below)

    # Notebook features
    enable_live_notebook=False,   # Save notebook after each execution
    enable_notebook_sync=False,   # Bidirectional sync with Jupyter

    # MCP tools
    mcp_config=None,              # Path to MCP YAML config
)
```

### Streaming Responses

```python
# Stream responses for real-time UI updates
for response in agent.chat_stream("Analyze this data"):
    if response.thinking:
        print(f"Thinking: {response.thinking}")
    if response.code:
        print(f"Executing: {response.code}")
    if response.execution_result:
        print(f"Output: {response.execution_result.output}")
    if response.has_answer:
        print(f"Answer: {response.answer}")
```

### Session Management

```python
from dsagent.session import SessionManager

# Create session manager
manager = SessionManager(Path("./workspace"))

# Create new session
session = manager.create_session(name="My Analysis")

# Use with agent
agent = ConversationalAgent(config, session=session, session_manager=manager)
agent.start(session)

# Chat...
agent.chat("Load data.csv")

# Session is automatically saved
# Later, resume it:
session = manager.load_session(session.id)
agent.start(session)  # Continues where you left off
```

### Response Object

The `chat()` method returns a `ChatResponse` object:

```python
response = agent.chat("Your message")

response.content        # Full response text
response.thinking       # Agent's reasoning (if any)
response.code           # Code that was executed (if any)
response.execution_result  # Code execution result
response.plan           # Current plan state
response.has_answer     # True if this is a final answer
response.answer         # Final answer text
```

---

## PlannerAgent

The `PlannerAgent` is designed for one-shot tasks that run autonomously with dynamic planning.

### Basic Usage

```python
from dsagent import PlannerAgent

# Using context manager (recommended)
with PlannerAgent(model="gpt-4o", data="./data.csv") as agent:
    result = agent.run("Analyze this dataset and create visualizations")
    print(result.answer)
    print(f"Notebook: {result.notebook_path}")
```

### Configuration Options

```python
from dsagent import PlannerAgent, RunContext

agent = PlannerAgent(
    # LLM settings
    model="gpt-4o",              # LLM model to use
    max_tokens=4096,             # Max tokens per response
    temperature=0.2,             # LLM temperature

    # Data and workspace
    data="./my_data.csv",        # Data file or directory
    workspace="./workspace",     # Working directory

    # Execution limits
    max_rounds=30,               # Max agent iterations
    timeout=300,                 # Code execution timeout (seconds)

    # Human-in-the-loop
    hitl=HITLMode.NONE,          # HITL mode

    # MCP tools
    mcp_config="~/.dsagent/mcp.yaml",  # MCP config path

    # Output
    verbose=True,                # Print to console
    event_callback=None,         # Callback for events
)
```

### Streaming Events

```python
from dsagent import PlannerAgent, EventType

agent = PlannerAgent(model="gpt-4o")
agent.start()

for event in agent.run_stream("Build a predictive model"):
    if event.type == EventType.PLAN_UPDATED:
        print(f"Plan: {event.plan.raw_text}")
    elif event.type == EventType.CODE_EXECUTING:
        print(f"Running code...")
    elif event.type == EventType.CODE_SUCCESS:
        print(f"Code succeeded")
    elif event.type == EventType.CODE_FAILED:
        print(f"Code failed: {event.error}")
    elif event.type == EventType.ANSWER_ACCEPTED:
        print(f"Answer: {event.message}")

result = agent.get_result()
agent.shutdown()
```

### Run Context

For isolated runs with organized output:

```python
from dsagent import PlannerAgent, RunContext

# Create isolated run context
context = RunContext(workspace="./workspace")
context.copy_data("./dataset")  # Copy data to run's folder

agent = PlannerAgent(model="gpt-4o", context=context)
agent.start()

# Run task
for event in agent.run_stream("Analyze the data"):
    pass

# Access run artifacts
print(f"Run ID: {context.run_id}")
print(f"Run path: {context.run_path}")
print(f"Notebooks: {context.notebooks_path}")
print(f"Artifacts: {context.artifacts_path}")
print(f"Logs: {context.logs_path}")

agent.shutdown()
```

### Result Object

The `run()` method returns a `RunResult` object:

```python
result = agent.run("Your task")

result.answer           # Final answer text
result.success          # True if task completed successfully
result.notebook_path    # Path to generated notebook
result.rounds           # Number of iterations used
result.total_tokens     # Total tokens consumed
```

---

## Human-in-the-Loop (HITL)

Both agents support configurable human oversight.

### HITL Modes

```python
from dsagent.schema.models import HITLMode

HITLMode.NONE            # Fully autonomous (default)
HITLMode.PLAN_ONLY       # Pause for plan approval
HITLMode.ON_ERROR        # Pause when errors occur
HITLMode.PLAN_AND_ANSWER # Pause for plan + final answer
HITLMode.FULL            # Pause for everything
```

### Handling HITL Events

```python
from dsagent import PlannerAgent, EventType, HITLMode

agent = PlannerAgent(model="gpt-4o", hitl=HITLMode.PLAN_ONLY)
agent.start()

for event in agent.run_stream("Complex analysis"):
    if event.type == EventType.HITL_AWAITING_PLAN_APPROVAL:
        print(f"Plan proposed:\n{event.plan.raw_text}")

        # Choose action:
        agent.approve()              # Approve the plan
        # agent.reject("Bad plan")   # Reject and abort
        # agent.modify_plan("...")   # Provide new plan

    elif event.type == EventType.HITL_AWAITING_CODE_APPROVAL:
        print(f"Code to run:\n{event.code}")
        agent.approve()              # Approve the code
        # agent.modify_code("...")   # Provide modified code
        # agent.skip()               # Skip this step

    elif event.type == EventType.HITL_AWAITING_ERROR_GUIDANCE:
        print(f"Error: {event.error}")
        agent.send_feedback("Try a different approach")
        # agent.skip()               # Skip this step
        # agent.reject("Abort")      # Abort execution

agent.shutdown()
```

### HITL Actions

```python
# Approve current pending item
agent.approve("Looks good!")

# Reject and abort
agent.reject("This approach won't work")

# Modify the plan
agent.modify_plan("""
1. [ ] Load the data
2. [ ] Clean missing values
3. [ ] Train model
""")

# Modify code before execution
agent.modify_code("import pandas as pd\ndf = pd.read_csv('data.csv')")

# Skip current step
agent.skip()

# Send feedback to guide the agent
agent.send_feedback("Try using a different algorithm")
```

---

## Event Types

```python
from dsagent import EventType

# Lifecycle events
EventType.AGENT_STARTED       # Agent started processing
EventType.AGENT_FINISHED      # Agent finished
EventType.AGENT_ERROR         # Error occurred

# Round events
EventType.ROUND_STARTED       # New iteration round
EventType.ROUND_FINISHED      # Round completed

# LLM events
EventType.LLM_CALL_STARTED    # LLM call started
EventType.LLM_CALL_FINISHED   # LLM response received

# Planning events
EventType.PLAN_CREATED        # Plan was created
EventType.PLAN_UPDATED        # Plan was updated

# Execution events
EventType.CODE_EXECUTING      # Code execution started
EventType.CODE_SUCCESS        # Code execution succeeded
EventType.CODE_FAILED         # Code execution failed

# Answer events
EventType.ANSWER_ACCEPTED     # Final answer generated
EventType.ANSWER_REJECTED     # Answer rejected (plan incomplete)

# HITL events
EventType.HITL_AWAITING_PLAN_APPROVAL
EventType.HITL_AWAITING_CODE_APPROVAL
EventType.HITL_AWAITING_ERROR_GUIDANCE
EventType.HITL_AWAITING_ANSWER_APPROVAL
EventType.HITL_PLAN_APPROVED
EventType.HITL_PLAN_MODIFIED
EventType.HITL_PLAN_REJECTED
EventType.HITL_FEEDBACK_RECEIVED
EventType.HITL_EXECUTION_ABORTED
```

---

## FastAPI Integration

Example of using DSAgent with FastAPI for a web API:

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from uuid import uuid4
from dsagent import PlannerAgent, EventType

app = FastAPI()

@app.post("/analyze")
async def analyze(task: str, data_path: str = None):
    async def event_stream():
        agent = PlannerAgent(
            model="gpt-4o",
            data=data_path,
            session_id=str(uuid4()),
        )
        agent.start()

        try:
            for event in agent.run_stream(task):
                yield f"data: {event.to_sse()}\n\n"
        finally:
            agent.shutdown()

    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.post("/chat")
async def chat(message: str, session_id: str = None):
    # For conversational interface, you'd need session management
    # See full example in examples/
    pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## Architecture

```
dsagent/
├── agents/
│   ├── base.py              # PlannerAgent
│   └── conversational.py    # ConversationalAgent
├── core/
│   ├── context.py           # RunContext
│   ├── engine.py            # AgentEngine
│   ├── executor.py          # JupyterExecutor
│   ├── hitl.py              # HITLGateway
│   └── planner.py           # PlanParser
├── session/
│   ├── manager.py           # SessionManager
│   ├── store.py             # SessionStore
│   └── models.py            # Session, Message
├── tools/
│   ├── config.py            # MCP configuration
│   └── mcp_manager.py       # MCPManager
├── schema/
│   └── models.py            # Pydantic models
└── utils/
    ├── logger.py            # Console logging
    ├── run_logger.py        # Structured logging
    └── notebook.py          # NotebookBuilder
```
