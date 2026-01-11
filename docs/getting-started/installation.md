# Installation

DSAgent can be installed via pip, Docker, or from source.

## Requirements

- Python 3.10 or higher
- An API key from a supported LLM provider (OpenAI, Anthropic, Google, etc.)

## pip (Recommended)

```bash
pip install datascience-agent
```

### Optional Dependencies

Install additional features as needed:

```bash
# API server support (FastAPI)
pip install "datascience-agent[api]"

# MCP tools support
pip install "datascience-agent[mcp]"

# All extras
pip install "datascience-agent[api,mcp]"
```

## Docker

Pull the official image from Docker Hub:

```bash
# Standard image (~1GB)
docker pull nmlemus/dsagent:latest

# Full image with LaTeX support (~1.5GB)
docker pull nmlemus/dsagent:full
```

See the [Docker Guide](../guide/docker.md) for detailed deployment instructions.

## From Source

For development or to get the latest features:

```bash
# Clone the repository
git clone https://github.com/nmlemus/dsagent
cd dsagent

# Install with uv (recommended)
uv sync --all-extras

# Or with pip
pip install -e ".[dev,api,mcp]"
```

## Verify Installation

Check that DSAgent is installed correctly:

```bash
dsagent --version
```

You should see output like:

```
dsagent 0.7.0
```

## Initial Setup

After installation, run the setup wizard to configure your LLM provider:

```bash
dsagent init
```

This interactive wizard will:

1. Ask for your preferred LLM provider
2. Prompt for your API key
3. Store credentials securely in `~/.dsagent/.env`
4. Optionally configure MCP tools

See [Configuration](configuration.md) for manual setup options.

## Next Steps

- [Quick Start](quickstart.md) - Learn the basics
- [Configuration](configuration.md) - Advanced setup options
- [Model Configuration](../guide/models.md) - Configure different LLM providers
