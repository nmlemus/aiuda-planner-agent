# MCP Tools Configuration

DSAgent supports the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) to connect to external tool servers, enabling capabilities like web search, database queries, file system access, and more.

## Installation

MCP support requires the optional dependency:

```bash
pip install "datascience-agent[mcp]"
```

## Quick Start

### 1. Add a Tool Server

Use the built-in templates to quickly add MCP servers:

```bash
# Add web search capability
dsagent mcp add brave-search
# You'll be prompted for your BRAVE_API_KEY

# Add file system access
dsagent mcp add filesystem
# You'll be prompted for paths to allow

# List configured servers
dsagent mcp list
```

### 2. Use with DSAgent

```bash
# Start chat with MCP tools enabled
dsagent --mcp-config ~/.dsagent/mcp.yaml
```

The agent can now use web search and other configured tools automatically.

---

## Configuration File

MCP servers are configured in a YAML file (default: `~/.dsagent/mcp.yaml`):

```yaml
servers:
  # Web search via Brave API
  - name: brave_search
    transport: stdio
    command: ["npx", "-y", "@modelcontextprotocol/server-brave-search"]
    env:
      BRAVE_API_KEY: "${BRAVE_API_KEY}"

  # Local file system access
  - name: filesystem
    transport: stdio
    command: ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed"]

  # GitHub repository access
  - name: github
    transport: stdio
    command: ["npx", "-y", "@modelcontextprotocol/server-github"]
    env:
      GITHUB_TOKEN: "${GITHUB_TOKEN}"

  # HTTP-based server (alternative transport)
  - name: custom_server
    transport: http
    url: "http://localhost:8080/mcp"
    enabled: false  # Disable without removing
```

### Configuration Options

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique identifier for the server |
| `transport` | string | `stdio` or `http` |
| `command` | list | Command to start stdio server |
| `url` | string | URL for http transport |
| `env` | object | Environment variables for the server |
| `enabled` | boolean | Enable/disable without removing (default: true) |

### Environment Variable Substitution

Use `${VAR_NAME}` syntax to reference environment variables:

```yaml
env:
  API_KEY: "${MY_API_KEY}"      # Resolved from environment
  STATIC_VALUE: "hardcoded"     # Static value
```

Environment variables are resolved at runtime from:
1. System environment
2. `~/.dsagent/.env` file
3. Current directory `.env` file

---

## Available MCP Server Templates

### brave-search

Web search capability using Brave Search API.

```bash
dsagent mcp add brave-search
```

**Required:** `BRAVE_API_KEY` - Get one at [brave.com/search/api](https://brave.com/search/api/)

**Package:** `@modelcontextprotocol/server-brave-search`

**Tools provided:**
- `brave_web_search` - Search the web

### filesystem

Secure access to local file system.

```bash
dsagent mcp add filesystem
```

**Required:** Paths to allow access (prompted during setup)

**Package:** `@modelcontextprotocol/server-filesystem`

**Tools provided:**
- `read_file` - Read file contents
- `write_file` - Write to files
- `list_directory` - List directory contents
- `create_directory` - Create directories

### github

GitHub repository access for reading issues, PRs, code, etc.

```bash
dsagent mcp add github
```

**Required:** `GITHUB_TOKEN` - Personal access token with repo scope

**Package:** `@modelcontextprotocol/server-github`

**Tools provided:**
- `search_repositories` - Search GitHub repos
- `get_file_contents` - Read files from repos
- `list_issues` - List repository issues
- `create_issue` - Create issues

### memory

Persistent memory/knowledge base for storing and retrieving information.

```bash
dsagent mcp add memory
```

**Required:** None

**Package:** `@modelcontextprotocol/server-memory`

**Tools provided:**
- `store_memory` - Store information
- `retrieve_memory` - Retrieve stored information

### fetch

Fetch and parse web content (HTML, JSON, etc.).

```bash
dsagent mcp add fetch
```

**Required:** None

**Package:** `@modelcontextprotocol/server-fetch`

**Tools provided:**
- `fetch` - Fetch URL content

---

## Python API

### Using MCP with ConversationalAgent

```python
from dsagent import ConversationalAgent, ConversationalAgentConfig
from pathlib import Path

config = ConversationalAgentConfig(
    model="gpt-4o",
    mcp_config=Path("~/.dsagent/mcp.yaml").expanduser(),
)

agent = ConversationalAgent(config)
agent.start()

# Agent can now use web search and other MCP tools
response = agent.chat("Search for the latest Python 3.13 features")
print(response.content)

agent.shutdown()
```

### Using MCP with PlannerAgent

```python
from dsagent import PlannerAgent

agent = PlannerAgent(
    model="gpt-4o",
    mcp_config="~/.dsagent/mcp.yaml",
)
agent.start()

for event in agent.run_stream("Research current AI trends and summarize"):
    if event.type == EventType.ANSWER_ACCEPTED:
        print(event.message)

agent.shutdown()
```

---

## Managing Servers

### List Servers

```bash
dsagent mcp list
```

Shows all configured servers with their status.

### Add Server

```bash
# From template
dsagent mcp add brave-search

# Templates available:
# - brave-search
# - filesystem
# - github
# - memory
# - fetch
```

### Remove Server

```bash
dsagent mcp remove brave_search
```

### Manual Configuration

Edit `~/.dsagent/mcp.yaml` directly for custom servers:

```yaml
servers:
  - name: my_custom_server
    transport: stdio
    command: ["python", "-m", "my_mcp_server"]
    env:
      MY_CONFIG: "value"
```

---

## Custom MCP Servers

You can connect to any MCP-compatible server:

### stdio Transport

For servers that communicate via stdin/stdout:

```yaml
servers:
  - name: my_server
    transport: stdio
    command: ["path/to/server", "--arg1", "value"]
    env:
      CONFIG_VAR: "value"
```

### HTTP Transport

For HTTP-based servers:

```yaml
servers:
  - name: my_http_server
    transport: http
    url: "http://localhost:8080/mcp"
```

---

## Troubleshooting

### "Server failed to start"

1. Check if the command is installed:
   ```bash
   npx -y @modelcontextprotocol/server-brave-search --help
   ```

2. Check if Node.js/npx is available:
   ```bash
   which npx
   ```

3. Check environment variables are set:
   ```bash
   echo $BRAVE_API_KEY
   ```

### "Tool not found"

1. Verify the server is configured:
   ```bash
   dsagent mcp list
   ```

2. Check the MCP config path is correct:
   ```bash
   dsagent --mcp-config ~/.dsagent/mcp.yaml
   ```

### Environment Variables Not Loading

Ensure variables are in one of these locations:
- System environment: `export BRAVE_API_KEY="..."`
- User config: `~/.dsagent/.env`
- Project config: `./.env`

---

## More Resources

- [MCP Specification](https://modelcontextprotocol.io/)
- [MCP Server Directory](https://github.com/modelcontextprotocol/servers)
- [Building MCP Servers](https://modelcontextprotocol.io/docs/build)
