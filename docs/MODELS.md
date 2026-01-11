# Model Configuration Guide

DSAgent uses [LiteLLM](https://docs.litellm.ai/) to support 100+ LLM providers with a unified interface. This guide covers setup for the most common providers.

## How It Works

LiteLLM automatically detects the provider from the model name and routes requests to the correct API endpoint. You only need to:

1. Set the API key for your provider (environment variable)
2. Specify the model name with `--model`

**Provider prefixes:**

| Provider | Prefix Required | Example |
|----------|-----------------|---------|
| OpenAI | No | `gpt-4o` |
| Anthropic | No | `claude-sonnet-4-5` |
| Google AI Studio | **Yes** | `gemini/gemini-2.5-flash` |
| DeepSeek | Yes | `deepseek/deepseek-chat` |
| Ollama | Yes | `ollama/llama3.2` |
| Azure | Yes | `azure/deployment-name` |

## Cloud Providers

### OpenAI

```bash
# Set API key
export OPENAI_API_KEY="sk-..."

# Use any OpenAI model
dsagent run "Your task" --model gpt-4o
dsagent run "Your task" --model gpt-4o-mini
dsagent run "Your task" --model o1
dsagent run "Your task" --model o3-mini
```

**Available models:** `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `o1`, `o1-mini`, `o3-mini`

### Anthropic (Claude)

```bash
# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Use any Claude model
dsagent run "Your task" --model claude-opus-4
dsagent run "Your task" --model claude-sonnet-4-5
dsagent run "Your task" --model claude-3-5-sonnet
dsagent run "Your task" --model claude-haiku-4-5
```

**Available models:** `claude-opus-4`, `claude-sonnet-4-5`, `claude-3-5-sonnet`, `claude-haiku-4-5`

### Google (Gemini)

```bash
# Set API key
export GOOGLE_API_KEY="..."

# Use any Gemini model (always use gemini/ prefix)
dsagent run "Your task" --model gemini/gemini-2.5-pro
dsagent run "Your task" --model gemini/gemini-2.5-flash
dsagent run "Your task" --model gemini/gemini-2.0-flash
```

**Available models:** `gemini/gemini-2.5-pro`, `gemini/gemini-2.5-flash`, `gemini/gemini-2.0-flash`, `gemini/gemini-1.5-pro`

> **Important:** Always use the `gemini/` prefix for Google AI Studio. Without the prefix, LiteLLM routes to Google Vertex AI, which requires different authentication (GCP credentials instead of API key).

### DeepSeek

```bash
# Set API key
export DEEPSEEK_API_KEY="..."

# Use DeepSeek models
dsagent run "Your task" --model deepseek/deepseek-chat
dsagent run "Your task" --model deepseek/deepseek-r1
```

**Available models:** `deepseek/deepseek-chat`, `deepseek/deepseek-r1`, `deepseek/deepseek-r1-distill-llama-70b`

### Azure OpenAI

```bash
# Set Azure credentials
export AZURE_API_KEY="..."
export AZURE_API_BASE="https://your-resource.openai.azure.com/"
export AZURE_API_VERSION="2024-02-15-preview"

# Use with azure/ prefix
dsagent run "Your task" --model azure/your-deployment-name
```

## Local Models

### Ollama

[Ollama](https://ollama.ai/) lets you run open-source LLMs locally. No API key required.

**Setup:**

```bash
# 1. Install Ollama
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# 2. Start the Ollama server
ollama serve

# 3. Pull a model
ollama pull llama3.2
ollama pull deepseek-r1:14b
ollama pull qwen2.5-coder
ollama pull codestral
```

**Usage:**

```bash
# Use with ollama/ prefix
dsagent run "Your task" --model ollama/llama3.2
dsagent run "Your task" --model ollama/deepseek-r1:14b
dsagent run "Your task" --model ollama/qwen2.5-coder
```

**Custom host/port:**

```bash
# If Ollama runs on a different machine
export OLLAMA_API_BASE="http://192.168.1.100:11434"
dsagent run "Your task" --model ollama/llama3.2
```

**Recommended models for data science:**
- `ollama/llama3.2` - Latest Llama, general purpose
- `ollama/deepseek-r1:14b` - Strong reasoning capabilities
- `ollama/qwen2.5-coder` - Excellent for code generation
- `ollama/codestral` - Mistral's coding model

### LM Studio

[LM Studio](https://lmstudio.ai/) provides a GUI for running local models with an OpenAI-compatible API.

**Setup:**

1. Download and install LM Studio
2. Download a model (e.g., Llama 3, Mistral, CodeLlama)
3. Start the local server (default: `http://localhost:1234/v1`)

**Usage:**

```bash
# Point to LM Studio's server
export OPENAI_API_BASE="http://localhost:1234/v1"
export OPENAI_API_KEY="not-needed"  # Required by LiteLLM but ignored by LM Studio

# Use with openai/ prefix
dsagent run "Your task" --model openai/local-model
```

**Note:** The model name after `openai/` doesn't matter much - LM Studio uses whatever model you have loaded.

### Other OpenAI-Compatible APIs

Any API that follows the OpenAI format can be used:

```bash
export OPENAI_API_BASE="https://your-api-endpoint.com/v1"
export OPENAI_API_KEY="your-api-key"

dsagent run "Your task" --model openai/model-name
```

## Python SDK

All models work the same way in the Python SDK:

```python
import os
from dsagent import PlannerAgent

# OpenAI
os.environ["OPENAI_API_KEY"] = "sk-..."
with PlannerAgent(model="gpt-4o") as agent:
    result = agent.run("Your task")

# Claude
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-..."
with PlannerAgent(model="claude-3-5-sonnet-20241022") as agent:
    result = agent.run("Your task")

# Ollama (no API key needed)
with PlannerAgent(model="ollama/llama3") as agent:
    result = agent.run("Your task")

# LM Studio
os.environ["OPENAI_API_BASE"] = "http://localhost:1234/v1"
os.environ["OPENAI_API_KEY"] = "not-needed"
with PlannerAgent(model="openai/local-model") as agent:
    result = agent.run("Your task")
```

## Troubleshooting

### "Connection error" with OpenAI

Check if you have `OPENAI_API_BASE` set to something wrong:

```bash
echo $OPENAI_API_BASE
# If it shows localhost or something unexpected:
unset OPENAI_API_BASE
```

### "API key not found"

Make sure the correct environment variable is set:

```bash
# Check what's set
env | grep -i api_key

# Set the right one for your model
export OPENAI_API_KEY="sk-..."      # for gpt-*
export ANTHROPIC_API_KEY="sk-ant-..." # for claude-*
export GOOGLE_API_KEY="..."          # for gemini-*
```

### Ollama "connection refused"

Make sure Ollama is running:

```bash
# Check if running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```

### Model validation error

DSAgent validates model names before starting. If you see an error like "gpt-5 does not exist", check for typos:

```bash
# Wrong
dsagent run "task" --model gpt4o      # Missing dash
dsagent run "task" --model gpt-5      # Doesn't exist

# Correct
dsagent run "task" --model gpt-4o
dsagent run "task" --model gpt-4-turbo
```

## More Information

- [LiteLLM Documentation](https://docs.litellm.ai/)
- [LiteLLM Supported Providers](https://docs.litellm.ai/docs/providers)
- [Ollama Model Library](https://ollama.ai/library)
