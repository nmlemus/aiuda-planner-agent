# Contributing

Thank you for your interest in contributing to DSAgent! This guide will help you get started.

## Development Setup

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- Git

### Clone and Install

```bash
# Clone the repository
git clone https://github.com/nmlemus/dsagent
cd dsagent

# Install with all development dependencies
uv sync --all-extras

# Or with pip
pip install -e ".[dev,api,mcp,docs]"
```

### Verify Setup

```bash
# Run tests
pytest

# Run linter
ruff check .

# Run type checker
mypy src/dsagent
```

## Project Structure

```
dsagent/
├── src/dsagent/
│   ├── agents/           # Agent implementations
│   │   ├── conversational.py
│   │   └── planner.py
│   ├── core/             # Core engine and execution
│   │   ├── engine.py
│   │   ├── kernel.py
│   │   └── session.py
│   ├── cli/              # Command-line interface
│   │   ├── main.py
│   │   └── repl.py
│   ├── server/           # API server
│   │   ├── app.py
│   │   └── routes/
│   └── schema/           # Data models
├── tests/                # Test suite
├── docs/                 # Documentation
└── pyproject.toml        # Project configuration
```

## Making Changes

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes

- Follow the existing code style
- Add tests for new functionality
- Update documentation if needed

### 3. Run Quality Checks

```bash
# Format code
ruff format .

# Check for issues
ruff check .

# Run type checker
mypy src/dsagent

# Run tests
pytest
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: Add your feature description"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub.

## Code Style

### Python

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use `ruff` for formatting and linting

### Documentation

- Use Google-style docstrings
- Document all public APIs
- Include examples in docstrings

```python
def analyze_data(data: pd.DataFrame, method: str = "auto") -> AnalysisResult:
    """Analyze a DataFrame using the specified method.

    Args:
        data: The DataFrame to analyze.
        method: Analysis method to use. Options: "auto", "statistical", "ml".

    Returns:
        AnalysisResult containing findings and visualizations.

    Raises:
        ValueError: If method is not recognized.

    Example:
        >>> result = analyze_data(df, method="statistical")
        >>> print(result.summary)
    """
```

## Testing

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=dsagent

# Specific test file
pytest tests/test_engine.py

# Specific test
pytest tests/test_engine.py::test_code_execution
```

### Writing Tests

```python
import pytest
from dsagent import PlannerAgent

def test_basic_execution():
    """Test basic agent execution."""
    with PlannerAgent(model="gpt-4o") as agent:
        result = agent.run("Print hello world")
        assert result.success
        assert "hello" in result.answer.lower()

@pytest.mark.asyncio
async def test_async_operation():
    """Test async functionality."""
    # async test code
```

## Documentation

### Building Docs Locally

```bash
# Install docs dependencies
pip install -e ".[docs]"

# Serve locally with hot reload
mkdocs serve

# Build static site
mkdocs build
```

Visit `http://localhost:8000` to preview.

### Documentation Structure

- `docs/` - Source markdown files
- `mkdocs.yml` - MkDocs configuration
- API docs are auto-generated from docstrings

## Releasing

Releases are automated via GitHub Actions:

1. Update version in `pyproject.toml`
2. Create a git tag: `git tag v0.x.x`
3. Push the tag: `git push origin v0.x.x`
4. Create GitHub Release

This triggers:
- PyPI package publishing
- Docker image build and push
- Documentation deployment

## Getting Help

- [GitHub Issues](https://github.com/nmlemus/dsagent/issues) - Bug reports and feature requests
- [Discussions](https://github.com/nmlemus/dsagent/discussions) - Questions and ideas

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
