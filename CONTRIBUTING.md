# Contributing to Aiuda Planner Agent

## Git Flow

This project follows Git Flow branching strategy.

### Branch Structure

```
main              ← Production (stable releases only)
  │
develop           ← Integration (development changes)
  │
  ├── feature/*   ← New features
  ├── bugfix/*    ← Bug fixes
  ├── release/*   ← Release preparation
  └── hotfix/*    ← Urgent production fixes
```

### Branch Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/short-description` | `feature/add-streaming-api` |
| Bug fix | `bugfix/issue-or-description` | `bugfix/fix-notebook-export` |
| Release | `release/vX.Y.Z` | `release/v0.2.0` |
| Hotfix | `hotfix/description` | `hotfix/critical-memory-leak` |

## Development Workflow

### 1. New Feature

```bash
# Start from develop
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/my-new-feature

# Work on your feature...
# Make commits with clear messages

# Push and create PR
git push -u origin feature/my-new-feature
```

Then create a Pull Request to `develop` on GitHub.

### 2. Bug Fix

```bash
# Start from develop
git checkout develop
git pull origin develop

# Create bugfix branch
git checkout -b bugfix/fix-issue-123

# Fix the bug...

# Push and create PR
git push -u origin bugfix/fix-issue-123
```

Then create a Pull Request to `develop` on GitHub.

### 3. Release

When `develop` is ready for a new release:

```bash
# Start from develop
git checkout develop
git pull origin develop

# Create release branch
git checkout -b release/v0.2.0

# Update version in pyproject.toml
# Update CHANGELOG if exists
# Final testing

# Push
git push -u origin release/v0.2.0
```

Then:
1. Create PR to `main`
2. After merge, tag the release: `git tag v0.2.0`
3. Merge back to `develop`

### 4. Hotfix (Urgent Production Fix)

```bash
# Start from main
git checkout main
git pull origin main

# Create hotfix branch
git checkout -b hotfix/critical-fix

# Fix the issue...

# Push
git push -u origin hotfix/critical-fix
```

Then:
1. Create PR to `main`
2. After merge, also merge to `develop`

## Commit Messages

Use clear, descriptive commit messages:

```
type: short description

Longer description if needed.

- Bullet points for multiple changes
- Another change
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance tasks

**Examples:**
```
feat: add streaming API endpoint

fix: resolve notebook cell ordering issue

docs: update README with CLI examples

refactor: simplify plan parsing logic
```

## Development Setup

```bash
# Clone repository
git clone https://github.com/nmlemus/aiuda-planner-agent.git
cd aiuda-planner-agent

# Create environment with uv
uv venv --python 3.11
source .venv/bin/activate

# Install with dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run linting
uv run ruff check .
```

## Code Style

- Use `ruff` for linting
- Use `mypy` for type checking
- Follow PEP 8 guidelines
- Add type hints to all functions
- Write docstrings for public APIs

```bash
# Check code style
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Type checking
uv run mypy src/
```

## Pull Request Checklist

Before submitting a PR:

- [ ] Code follows project style guidelines
- [ ] Tests pass locally
- [ ] New features have tests
- [ ] Documentation updated if needed
- [ ] Commit messages are clear
- [ ] PR description explains the changes

## Questions?

Open an issue on GitHub for any questions or discussions.
