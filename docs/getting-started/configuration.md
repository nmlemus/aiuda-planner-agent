# Configuration

DSAgent can be configured through environment variables, configuration files, or command-line arguments.

## Configuration Methods

Configuration is loaded in this order (later sources override earlier):

1. Default values
2. Environment variables
3. `.env` file in `~/.dsagent/`
4. `.env` file in current directory
5. Command-line arguments

## Environment Variables

### LLM Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_MODEL` | LLM model to use | `gpt-4o` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `GOOGLE_API_KEY` | Google API key | - |
| `DEEPSEEK_API_KEY` | DeepSeek API key | - |
| `LLM_API_BASE` | Custom API endpoint | - |
| `OLLAMA_API_BASE` | Ollama server URL | `http://localhost:11434` |

### Agent Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `DSAGENT_MAX_ROUNDS` | Maximum agent iterations | `30` |
| `DSAGENT_TEMPERATURE` | LLM temperature (0.0-1.0) | `0.3` |
| `DSAGENT_MAX_TOKENS` | Max tokens per response | `4096` |
| `DSAGENT_CODE_TIMEOUT` | Code execution timeout (seconds) | `300` |
| `DSAGENT_WORKSPACE` | Workspace directory | `./workspace` |

### API Server

| Variable | Description | Default |
|----------|-------------|---------|
| `DSAGENT_API_KEY` | API authentication key | - (disabled) |
| `DSAGENT_CORS_ORIGINS` | CORS allowed origins | `*` |

## Configuration File

Create a `.env` file in `~/.dsagent/` for persistent configuration:

```bash
# ~/.dsagent/.env

# LLM Configuration
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-your-key-here

# Agent Settings
DSAGENT_MAX_ROUNDS=30
DSAGENT_TEMPERATURE=0.3
```

The setup wizard (`dsagent init`) creates this file automatically.

## Command-Line Options

Override settings per-session:

```bash
# Use a different model
dsagent --model claude-sonnet-4-5

# Custom workspace
dsagent --workspace /path/to/workspace

# Resume a session
dsagent --session abc123

# Enable human-in-the-loop
dsagent --hitl plan
```

## Human-in-the-Loop Modes

Control when the agent asks for approval:

| Mode | Description |
|------|-------------|
| `none` | No approval required (default) |
| `plan` | Approve plan before execution |
| `full` | Approve plan and each code block |
| `plan_answer` | Approve plan and final answer |
| `on_error` | Ask for guidance on errors |

```bash
dsagent --hitl plan
```

## MCP Tools Configuration

MCP tools are configured in `~/.dsagent/mcp.yaml`:

```yaml
mcpServers:
  brave-search:
    command: npx
    args: ["-y", "@anthropic/mcp-brave-search"]
    env:
      BRAVE_API_KEY: "your-brave-api-key"
```

Add tools using the CLI:

```bash
dsagent mcp add brave-search
dsagent mcp add filesystem
```

See [MCP Tools](../guide/mcp.md) for available tools and configuration.

## Workspace Structure

DSAgent organizes output in the workspace directory:

```
workspace/
├── sessions/
│   └── {session_id}/
│       ├── session.json    # Session metadata
│       ├── messages.json   # Conversation history
│       └── kernel_state/   # Jupyter kernel state
└── runs/
    └── {run_id}/
        ├── data/           # Input data (copied)
        ├── notebooks/      # Generated notebooks
        ├── artifacts/      # Charts, models, exports
        └── logs/           # Execution logs
```

## Proxy Configuration

For corporate environments or custom endpoints:

```bash
# Use a proxy server
export LLM_API_BASE="https://your-proxy.com/v1"
export OPENAI_API_KEY="your-proxy-key"

# Route through LiteLLM proxy
dsagent --model openai/gpt-4o
```

## Docker Configuration

See [Docker Guide](../guide/docker.md) for container-specific configuration options.
