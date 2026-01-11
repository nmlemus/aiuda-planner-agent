# Architecture

This document describes the internal architecture of DSAgent.

## Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │     CLI     │  │  Python API │  │      REST/WebSocket     │  │
│  └──────┬──────┘  └──────┬──────┘  └────────────┬────────────┘  │
└─────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                      │
          ▼                ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                           Agents                                │
│  ┌─────────────────────┐      ┌─────────────────────────────┐   │
│  │   PlannerAgent      │      │   ConversationalAgent       │   │
│  │   (one-shot tasks)  │      │   (multi-turn sessions)     │   │
│  └──────────┬──────────┘      └──────────────┬──────────────┘   │
└─────────────┼────────────────────────────────┼──────────────────┘
              │                                │
              ▼                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Core Engine                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Planner   │  │   Executor  │  │    Session Manager      │  │
│  └──────┬──────┘  └──────┬──────┘  └────────────┬────────────┘  │
└─────────┼────────────────┼──────────────────────┼───────────────┘
          │                │                      │
          ▼                ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Infrastructure                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   LiteLLM   │  │   Jupyter   │  │      MCP Client         │  │
│  │  (LLM API)  │  │   Kernel    │  │   (External Tools)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### Agents

#### PlannerAgent

The `PlannerAgent` handles one-shot tasks:

1. Receives a task description
2. Creates an execution plan
3. Executes plan steps sequentially
4. Returns structured results

```python
# src/dsagent/agents/planner.py
class PlannerAgent:
    def __init__(self, config: AgentConfig):
        self.engine = PlannerEngine(config)

    def run(self, task: str) -> AgentResult:
        plan = self.engine.create_plan(task)
        return self.engine.execute_plan(plan)
```

#### ConversationalAgent

The `ConversationalAgent` handles interactive sessions:

1. Maintains conversation history
2. Manages session persistence
3. Supports streaming responses
4. Handles context summarization

```python
# src/dsagent/agents/conversational.py
class ConversationalAgent:
    def __init__(self, config: ConversationalAgentConfig):
        self.session = SessionManager(config)
        self.engine = ConversationalEngine(config)

    def chat(self, message: str) -> ChatResponse:
        self.session.add_message("user", message)
        response = self.engine.process(self.session)
        self.session.add_message("assistant", response)
        return response
```

### Core Engine

#### Planner

Creates execution plans from task descriptions:

```python
class Planner:
    def create_plan(self, task: str, context: Context) -> Plan:
        # 1. Analyze task requirements
        # 2. Break down into steps
        # 3. Identify dependencies
        # 4. Return structured plan
```

#### Executor

Executes code in the Jupyter kernel:

```python
class Executor:
    def __init__(self):
        self.kernel = JupyterKernel()

    def execute(self, code: str) -> ExecutionResult:
        # 1. Send code to kernel
        # 2. Capture output/errors
        # 3. Handle timeouts
        # 4. Return result
```

#### Session Manager

Handles session persistence:

```python
class SessionManager:
    def save(self, session_id: str):
        # Save conversation history
        # Save kernel state (variables)
        # Save metadata

    def load(self, session_id: str):
        # Restore conversation
        # Restore kernel state
```

### Infrastructure

#### LiteLLM Integration

All LLM calls go through LiteLLM for provider abstraction:

```python
from litellm import completion

response = completion(
    model="gpt-4o",  # or "claude-sonnet-4-5", "gemini/gemini-2.5-flash"
    messages=messages,
    temperature=0.3,
)
```

#### Jupyter Kernel

Code execution uses `jupyter_client`:

```python
from jupyter_client import KernelManager

class JupyterKernel:
    def __init__(self):
        self.km = KernelManager(kernel_name='python3')
        self.km.start_kernel()
        self.client = self.km.client()

    def execute(self, code: str) -> str:
        self.client.execute(code)
        # Handle messages...
```

#### MCP Client

External tools via Model Context Protocol:

```python
class MCPClient:
    def __init__(self, config_path: str):
        self.servers = load_mcp_config(config_path)

    async def call_tool(self, server: str, tool: str, args: dict):
        # Connect to MCP server
        # Call tool with arguments
        # Return result
```

## Data Flow

### One-Shot Task (PlannerAgent)

```
User Task
    │
    ▼
┌─────────┐
│ Planner │ ──► LLM creates plan
└────┬────┘
     │
     ▼
┌──────────┐     ┌─────────┐
│ Executor │ ◄──►│ Kernel  │  Execute each step
└────┬─────┘     └─────────┘
     │
     ▼
┌──────────┐
│ Reporter │ ──► Generate notebook + answer
└────┬─────┘
     │
     ▼
AgentResult
```

### Interactive Chat (ConversationalAgent)

```
User Message
    │
    ▼
┌──────────────┐
│   Session    │ ──► Load context/history
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌─────────┐
│    Engine    │ ◄──►│   LLM   │  Generate response
└──────┬───────┘     └─────────┘
       │
       ▼
┌──────────────┐     ┌─────────┐
│   Executor   │ ◄──►│ Kernel  │  Execute code (if any)
└──────┬───────┘     └─────────┘
       │
       ▼
┌──────────────┐
│   Session    │ ──► Save updated state
└──────┬───────┘
       │
       ▼
ChatResponse
```

## Key Design Decisions

### 1. Persistent Jupyter Kernel

Variables persist across messages, enabling natural multi-step analysis:

```python
# Message 1: Load data
df = pd.read_csv("data.csv")

# Message 2: df is still available
df.describe()
```

### 2. LiteLLM for Provider Abstraction

Single interface for 100+ LLM providers without code changes.

### 3. Session-Based Architecture

Sessions encapsulate:
- Conversation history
- Kernel state (variables)
- Generated artifacts

This enables:
- Resume interrupted work
- Share analysis state
- Export clean notebooks

### 4. MCP for Extensibility

External tools (web search, databases) via standardized protocol instead of hardcoded integrations.

## Extension Points

### Adding a New Agent Type

1. Create agent class in `src/dsagent/agents/`
2. Implement required interface
3. Add CLI command if needed

### Adding MCP Tool Templates

1. Add template to `src/dsagent/mcp/templates/`
2. Update template registry

### Custom LLM Providers

LiteLLM handles most providers. For custom endpoints:

```python
export LLM_API_BASE="https://your-endpoint.com/v1"
dsagent --model openai/your-model
```

## Performance Considerations

### Memory Management

- Sessions are loaded on-demand
- Large artifacts stored on disk
- Conversation summarization for long sessions

### Kernel Lifecycle

- Kernel started lazily (first code execution)
- Kernel reused within session
- Explicit cleanup on shutdown

### Streaming

- Responses streamed for better UX
- Code execution results streamed
- Reduces perceived latency
