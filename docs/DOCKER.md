# Docker Guide

DSAgent provides Docker images for easy deployment of both the CLI and API server.

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/nmlemus/dsagent
   cd dsagent
   ```

2. **Set your API key:**
   ```bash
   export OPENAI_API_KEY=sk-your-key-here
   # Or for other providers:
   # export ANTHROPIC_API_KEY=sk-ant-...
   # export GOOGLE_API_KEY=...
   ```

3. **Start the API server:**
   ```bash
   docker-compose up -d
   ```

4. **Access the API:**
   - API docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health

### Using Docker Hub

```bash
# Pull the image
docker pull nmlemus/dsagent:latest

# Run API server
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-your-key \
  -v $(pwd)/workspace:/workspace \
  nmlemus/dsagent:latest

# Run interactive CLI
docker run -it \
  -e OPENAI_API_KEY=sk-your-key \
  -v $(pwd)/workspace:/workspace \
  nmlemus/dsagent:latest \
  dsagent chat
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_MODEL` | LLM model to use | `gpt-4o` |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `GOOGLE_API_KEY` | Google API key | - |
| `DSAGENT_API_KEY` | API authentication key | - (disabled) |
| `DSAGENT_CORS_ORIGINS` | CORS allowed origins | `*` |

### Volumes

| Path | Description |
|------|-------------|
| `/workspace` | Session data, notebooks, artifacts |
| `/home/dsagent/.dsagent` | User configuration |

## Usage Examples

### API Server Mode

```bash
# Start server with default settings
docker-compose up -d

# Start with specific model
LLM_MODEL=claude-sonnet-4-5 ANTHROPIC_API_KEY=sk-ant-... docker-compose up -d

# View logs
docker-compose logs -f dsagent

# Stop server
docker-compose down
```

### Interactive CLI Mode

```bash
# Using docker-compose
docker-compose run --rm dsagent-cli

# Or directly with docker
docker run -it \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -v $(pwd)/workspace:/workspace \
  nmlemus/dsagent:latest \
  dsagent chat
```

### One-Shot Task

```bash
docker run --rm \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -v $(pwd)/workspace:/workspace \
  -v $(pwd)/data.csv:/workspace/data.csv \
  nmlemus/dsagent:latest \
  dsagent run "Analyze this dataset" --data /workspace/data.csv
```

## Building Locally

```bash
# Build the image
docker build -t dsagent:local .

# Run with local build
docker run -it \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  dsagent:local \
  dsagent chat
```

## Docker Compose Profiles

The `docker-compose.yml` includes two services:

1. **dsagent** (default): API server on port 8000
2. **dsagent-cli** (profile: cli): Interactive CLI

```bash
# Start API server only
docker-compose up -d

# Start CLI session
docker-compose --profile cli run --rm dsagent-cli
```

## Security Notes

- The container runs as a non-root user (`dsagent`)
- API key authentication is optional but recommended for production
- Use `DSAGENT_API_KEY` to enable API authentication
- Restrict `DSAGENT_CORS_ORIGINS` in production

## Troubleshooting

### Container won't start

Check logs:
```bash
docker-compose logs dsagent
```

### API key not working

Ensure the environment variable is passed correctly:
```bash
docker run -e OPENAI_API_KEY="$OPENAI_API_KEY" ...
```

### Permission denied on workspace

The container user needs write access:
```bash
chmod 777 ./workspace
# Or run as root (not recommended):
docker run --user root ...
```
