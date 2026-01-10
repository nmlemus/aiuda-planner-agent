# DSAgent Scaling Proposal

## Executive Summary

This document outlines a scaling strategy for DSAgent that enables it to grow from a CLI tool to a full-featured platform with UI, while maintaining backward compatibility with `pip install dsagent`.

The key principle: **Core always works standalone, extras are optional**.

---

## Current State

DSAgent is currently a CLI-based data science agent:

```bash
pip install dsagent
dsagent chat --model gpt-4o
dsagent run "Analyze sales.csv" --data sales.csv
```

**Current architecture:**
- ConversationalAgent with plan-and-execute loop
- Local IPython kernel for code execution
- SQLite for session persistence
- Local filesystem for data/artifacts
- MCP integration for external tools

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           dsagent (core)                                 │
│  pip install dsagent                                                     │
│  ─────────────────────────────────────────────────────────────────────  │
│  • ConversationalAgent, PlannerAgent                                     │
│  • Kernel management (local IPython)                                     │
│  • Session models, MCP tools                                             │
│  • CLI (dsagent chat, dsagent run)                                       │
│  • Storage: SQLite + local filesystem (default)                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌───────────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐
│   dsagent[api]        │ │  dsagent[db]    │ │   dsagent[storage]      │
│   ──────────────────  │ │  ─────────────  │ │   ─────────────────────  │
│   • FastAPI server    │ │  • PostgreSQL   │ │   • S3 backend          │
│   • WebSocket         │ │  • Redis cache  │ │   • GCS backend         │
│   • REST endpoints    │ │  • Migrations   │ │   • Azure Blob          │
│   • dsagent serve     │ │                 │ │                         │
└───────────────────────┘ └─────────────────┘ └─────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │      dsagent-ui (separate)    │
                    │      ───────────────────────  │
                    │      • Next.js / React        │
                    │      • Connects to API        │
                    │      • Can be hosted anywhere │
                    └───────────────────────────────┘
```

---

## Installation Tiers

### Tier 1: CLI Only (Default)
```bash
pip install dsagent
```
- Full CLI functionality
- SQLite persistence
- Local filesystem storage
- Single user, local execution

### Tier 2: With API Server
```bash
pip install dsagent[api]
```
- Everything in Tier 1
- REST API + WebSocket server
- SSE streaming
- Multi-client support
- `dsagent serve` command

### Tier 3: Production Database
```bash
pip install dsagent[api,db]
```
- Everything in Tier 2
- PostgreSQL support
- Redis caching
- Database migrations (Alembic)
- Connection pooling

### Tier 4: Cloud Storage
```bash
pip install dsagent[api,db,storage]
```
- Everything in Tier 3
- S3/MinIO file storage
- GCS support
- Azure Blob support

### Tier 5: Full Stack
```bash
pip install dsagent[all]
# Plus: dsagent-ui (separate package or Docker)
```
- Everything above
- Web UI

---

## Package Structure

```
dsagent/
├── src/dsagent/
│   │
│   │   # ============ CORE (always included) ============
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py              # PlannerAgent
│   │   └── conversational.py    # ConversationalAgent
│   │
│   ├── kernel/
│   │   ├── __init__.py
│   │   ├── backend.py           # ExecutorBackend ABC
│   │   ├── local.py             # LocalExecutor (IPython)
│   │   └── introspector.py      # KernelIntrospector
│   │
│   ├── session/
│   │   ├── __init__.py
│   │   ├── models.py            # Session, Message, etc.
│   │   ├── manager.py           # SessionManager
│   │   ├── store.py             # SessionStore (SQLite/JSON)
│   │   └── logger.py            # SessionLogger
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── main.py              # Entry point
│   │   ├── repl.py              # Interactive chat
│   │   ├── run.py               # One-shot execution
│   │   └── commands.py          # Slash commands
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   └── mcp_manager.py       # MCP integration
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── engine.py            # AgentEngine
│   │   ├── executor.py          # JupyterExecutor
│   │   └── planner.py           # PlanParser
│   │
│   │   # ============ API [api] ============
│   ├── server/
│   │   ├── __init__.py
│   │   ├── app.py               # FastAPI application
│   │   ├── deps.py              # Dependencies & auth
│   │   ├── manager.py           # ConnectionManager
│   │   ├── models.py            # API models
│   │   ├── websocket.py         # WebSocket endpoint
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── health.py
│   │       ├── sessions.py
│   │       ├── chat.py
│   │       ├── kernel.py
│   │       ├── files.py         # NEW: File upload/download
│   │       └── config.py        # NEW: Runtime config
│   │
│   │   # ============ DATABASE [db] ============
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py              # DatabaseBackend ABC
│   │   ├── postgres.py          # PostgreSQL implementation
│   │   ├── redis_cache.py       # Redis caching layer
│   │   └── migrations/
│   │       ├── env.py           # Alembic config
│   │       └── versions/        # Migration files
│   │
│   │   # ============ STORAGE [storage] ============
│   └── storage/
│       ├── __init__.py
│       ├── base.py              # StorageBackend ABC
│       ├── local.py             # Local filesystem (default)
│       ├── s3.py                # AWS S3 / MinIO
│       ├── gcs.py               # Google Cloud Storage
│       └── azure.py             # Azure Blob Storage
│
├── ui/                          # Separate: dsagent-ui
│   ├── package.json
│   ├── next.config.js
│   └── src/
│       ├── app/
│       ├── components/
│       └── lib/
│
├── pyproject.toml
├── docker-compose.yml           # Full stack deployment
└── Dockerfile
```

---

## Abstract Interfaces

### StorageBackend

```python
# src/dsagent/storage/base.py

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, BinaryIO

class StorageBackend(ABC):
    """Abstract interface for file storage."""

    @abstractmethod
    async def upload(
        self,
        session_id: str,
        filename: str,
        data: BinaryIO,
        content_type: Optional[str] = None
    ) -> str:
        """Upload a file. Returns the storage URL/path."""
        pass

    @abstractmethod
    async def download(self, session_id: str, filename: str) -> bytes:
        """Download a file's contents."""
        pass

    @abstractmethod
    async def list_files(
        self,
        session_id: str,
        prefix: str = "",
        category: str = "data"  # data, artifacts, notebooks
    ) -> List[dict]:
        """List files in a session. Returns list of {name, size, modified}."""
        pass

    @abstractmethod
    async def delete(self, session_id: str, filename: str) -> bool:
        """Delete a file. Returns True if deleted."""
        pass

    @abstractmethod
    async def get_url(
        self,
        session_id: str,
        filename: str,
        expires_in: int = 3600
    ) -> str:
        """Get a URL to access the file (signed URL for cloud storage)."""
        pass
```

### DatabaseBackend

```python
# src/dsagent/db/base.py

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dsagent.session.models import Session, SessionStatus

class DatabaseBackend(ABC):
    """Abstract interface for session database."""

    @abstractmethod
    async def save_session(self, session: Session) -> None:
        """Save or update a session."""
        pass

    @abstractmethod
    async def load_session(self, session_id: str) -> Optional[Session]:
        """Load a session by ID."""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        pass

    @abstractmethod
    async def list_sessions(
        self,
        user_id: Optional[str] = None,
        status: Optional[SessionStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List sessions with optional filtering."""
        pass

    @abstractmethod
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """Add a message to session history. Returns message ID."""
        pass

    @abstractmethod
    async def get_messages(
        self,
        session_id: str,
        limit: int = 100,
        before_id: Optional[str] = None
    ) -> List[Dict]:
        """Get messages for a session with pagination."""
        pass
```

### CacheBackend

```python
# src/dsagent/db/cache.py

from abc import ABC, abstractmethod
from typing import Optional, Any

class CacheBackend(ABC):
    """Abstract interface for caching."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        pass

    @abstractmethod
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> None:
        """Set a value in cache with optional TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass
```

---

## Configuration

### Environment Variables

```bash
# =============================================================================
# CORE SETTINGS
# =============================================================================

# LLM Configuration
LLM_MODEL=gpt-4o                          # Default model
LLM_API_KEY=sk-...                        # OpenAI API key
ANTHROPIC_API_KEY=sk-ant-...              # Anthropic API key
LLM_API_BASE=                             # Optional: LiteLLM proxy URL

# =============================================================================
# SERVER SETTINGS [api]
# =============================================================================

DSAGENT_HOST=0.0.0.0                      # Server host
DSAGENT_PORT=8000                         # Server port
DSAGENT_API_KEY=                          # API key for auth (optional)
DSAGENT_CORS_ORIGINS=*                    # Allowed CORS origins
DSAGENT_LOG_LEVEL=info                    # Logging level

# =============================================================================
# DATABASE SETTINGS [db]
# =============================================================================

# SQLite (default)
DSAGENT_DATABASE_URL=sqlite:///./workspace/.dsagent/sessions.db

# PostgreSQL (production)
DSAGENT_DATABASE_URL=postgresql://user:pass@localhost:5432/dsagent

# Connection pool settings
DSAGENT_DB_POOL_SIZE=5
DSAGENT_DB_MAX_OVERFLOW=10

# Redis cache (optional)
DSAGENT_REDIS_URL=redis://localhost:6379/0
DSAGENT_CACHE_TTL=3600                    # Default cache TTL in seconds

# =============================================================================
# STORAGE SETTINGS [storage]
# =============================================================================

# Local filesystem (default)
DSAGENT_STORAGE_TYPE=local
DSAGENT_STORAGE_PATH=./workspace

# AWS S3
DSAGENT_STORAGE_TYPE=s3
DSAGENT_S3_BUCKET=my-dsagent-bucket
DSAGENT_S3_REGION=us-east-1
DSAGENT_S3_ACCESS_KEY=AKIA...
DSAGENT_S3_SECRET_KEY=...
DSAGENT_S3_ENDPOINT=                      # Optional: MinIO endpoint

# Google Cloud Storage
DSAGENT_STORAGE_TYPE=gcs
DSAGENT_GCS_BUCKET=my-dsagent-bucket
DSAGENT_GCS_PROJECT=my-project
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Azure Blob Storage
DSAGENT_STORAGE_TYPE=azure
DSAGENT_AZURE_CONTAINER=dsagent
DSAGENT_AZURE_CONNECTION_STRING=...

# =============================================================================
# EXECUTION SETTINGS (Future)
# =============================================================================

# Kernel execution mode
DSAGENT_EXECUTOR_TYPE=local               # local, docker, kubernetes

# Docker execution
DSAGENT_DOCKER_IMAGE=dsagent/kernel:latest
DSAGENT_DOCKER_MEMORY_LIMIT=8g
DSAGENT_DOCKER_CPU_LIMIT=2

# =============================================================================
# UI SETTINGS
# =============================================================================

DSAGENT_UI_ENABLED=true                   # Serve UI from API server
DSAGENT_UI_PATH=/app/ui/dist              # Path to built UI files
```

### Configuration Priority

1. Environment variables
2. `.env` file in current directory
3. `~/.dsagent/.env` (user config)
4. Default values

---

## Deployment Scenarios

### Scenario 1: Local Development (CLI)

```bash
pip install dsagent
dsagent chat
```

```
┌──────────────┐
│   Terminal   │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐
│   DSAgent    │────▶│   SQLite     │
│   CLI        │     │   Local FS   │
└──────────────┘     └──────────────┘
```

### Scenario 2: Single Server with UI

```bash
pip install dsagent[api]
dsagent serve --port 8000
```

```
┌──────────────┐     ┌──────────────┐
│   Browser    │────▶│   DSAgent    │
│   (UI)       │     │   Server     │
└──────────────┘     └──────┬───────┘
                            │
                     ┌──────┴───────┐
                     ▼              ▼
              ┌──────────┐   ┌──────────┐
              │  SQLite  │   │ Local FS │
              └──────────┘   └──────────┘
```

### Scenario 3: Production (Multi-user)

```bash
pip install dsagent[all]
# Configure PostgreSQL, Redis, S3
dsagent serve
```

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Browser    │────▶│   Load       │────▶│   DSAgent    │
│   (UI)       │     │   Balancer   │     │   Server x N │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                     ┌────────────────────────────┼────────────────────────────┐
                     │                            │                            │
                     ▼                            ▼                            ▼
              ┌──────────────┐           ┌──────────────┐            ┌──────────────┐
              │  PostgreSQL  │           │    Redis     │            │      S3      │
              │  (sessions)  │           │   (cache)    │            │   (files)    │
              └──────────────┘           └──────────────┘            └──────────────┘
```

### Scenario 4: Kubernetes

```yaml
# docker-compose.yml (development)
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DSAGENT_DATABASE_URL=postgresql://postgres:postgres@db:5432/dsagent
      - DSAGENT_REDIS_URL=redis://redis:6379/0
      - DSAGENT_STORAGE_TYPE=s3
      - DSAGENT_S3_ENDPOINT=http://minio:9000
      - DSAGENT_S3_BUCKET=dsagent
    depends_on:
      - db
      - redis
      - minio

  ui:
    build: ./ui
    ports:
      - "3000:3000"
    environment:
      - API_URL=http://api:8000

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=dsagent
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

---

## API Endpoints (Complete)

### Health & Info
```
GET  /health                              # Health check
GET  /health/ready                        # Readiness check
GET  /info                                # Server info & version
```

### Sessions
```
POST   /api/sessions                      # Create session
GET    /api/sessions                      # List sessions
GET    /api/sessions/{id}                 # Get session
PUT    /api/sessions/{id}                 # Update session
DELETE /api/sessions/{id}                 # Delete session
POST   /api/sessions/{id}/archive         # Archive session
```

### Chat
```
POST   /api/sessions/{id}/chat            # Send message (sync)
POST   /api/sessions/{id}/chat/stream     # Send message (SSE)
GET    /api/sessions/{id}/messages        # Get message history
WS     /ws/chat/{id}                      # WebSocket chat
```

### Kernel
```
GET    /api/sessions/{id}/kernel          # Get kernel state
GET    /api/sessions/{id}/kernel/variables # List variables
POST   /api/sessions/{id}/kernel/execute  # Execute code
POST   /api/sessions/{id}/kernel/reset    # Reset kernel
```

### Files (NEW)
```
POST   /api/sessions/{id}/files           # Upload file(s)
GET    /api/sessions/{id}/files           # List files
GET    /api/sessions/{id}/files/{name}    # Download file
DELETE /api/sessions/{id}/files/{name}    # Delete file
```

### Artifacts (NEW)
```
GET    /api/sessions/{id}/artifacts       # List artifacts
GET    /api/sessions/{id}/artifacts/{name} # Download artifact
```

### Notebooks
```
GET    /api/sessions/{id}/notebook        # Export as notebook
POST   /api/sessions/{id}/notebook/sync   # Sync with external notebook
```

### Configuration (NEW)
```
GET    /api/sessions/{id}/config          # Get session config
PUT    /api/sessions/{id}/config          # Update config
POST   /api/sessions/{id}/reload          # Reload agent with new config
```

### MCP Tools (NEW)
```
GET    /api/mcp/templates                 # List available MCP templates
GET    /api/sessions/{id}/mcp             # List session MCPs
POST   /api/sessions/{id}/mcp             # Add MCP to session
PUT    /api/sessions/{id}/mcp/{name}      # Update MCP config
DELETE /api/sessions/{id}/mcp/{name}      # Remove MCP
```

### Models (NEW)
```
GET    /api/models                        # List available models
GET    /api/models/{name}/validate        # Validate model has API key
```

---

## Implementation Phases

### Phase 1: Foundation (Current)
- [x] Core agent (ConversationalAgent)
- [x] CLI (dsagent chat, run)
- [x] Session persistence (SQLite)
- [x] API server basics (FastAPI)
- [x] WebSocket + SSE streaming
- [x] Basic authentication

### Phase 2: API Completion
- [ ] File upload/download endpoints
- [ ] Artifacts endpoints
- [ ] Config update + reload
- [ ] Models listing
- [ ] Fix workspace structure

### Phase 3: Storage Abstraction
- [ ] StorageBackend interface
- [ ] Local filesystem implementation
- [ ] S3 implementation
- [ ] Configuration via env vars

### Phase 4: Database Abstraction
- [ ] DatabaseBackend interface
- [ ] PostgreSQL implementation
- [ ] Alembic migrations
- [ ] Connection pooling

### Phase 5: Caching
- [ ] CacheBackend interface
- [ ] Redis implementation
- [ ] Session caching
- [ ] Rate limiting

### Phase 6: UI
- [ ] Next.js project setup
- [ ] Authentication flow
- [ ] Session management UI
- [ ] Chat interface
- [ ] File browser
- [ ] Code editor

### Phase 7: Advanced Execution
- [ ] Docker kernel execution
- [ ] Resource limits
- [ ] Kubernetes support
- [ ] Multi-tenant isolation

---

## Security Considerations

### Authentication
- API Key authentication (current)
- JWT tokens (future)
- OAuth2/OIDC integration (future)

### Authorization
- Session ownership
- Role-based access control (admin, user)
- Team/organization support

### Isolation
- Kernel sandboxing
- File access restrictions
- Network policies

### Secrets Management
- Environment variables
- Vault integration (future)
- Encrypted storage for credentials

---

## Monitoring & Observability

### Metrics
- Request latency
- Active sessions
- LLM token usage
- Execution time
- Error rates

### Logging
- Structured JSON logs
- Request tracing
- Session event logs

### Health Checks
- Database connectivity
- Redis connectivity
- Storage accessibility
- LLM provider status

---

## References

### Similar Projects
- [MLflow](https://mlflow.org/) - ML lifecycle management
- [Prefect](https://www.prefect.io/) - Workflow orchestration
- [Julius.ai](https://julius.ai/) - AI data analysis
- [JupyterHub](https://jupyter.org/hub) - Multi-user Jupyter

### Technologies
- [FastAPI](https://fastapi.tiangolo.com/) - API framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [Alembic](https://alembic.sqlalchemy.org/) - Migrations
- [Redis](https://redis.io/) - Caching
- [MinIO](https://min.io/) - S3-compatible storage
- [Next.js](https://nextjs.org/) - React framework

---

## Appendix: pyproject.toml

```toml
[project]
name = "datascience-agent"
version = "0.7.0"
description = "AI Agent for data science with CLI, API, and UI support"

dependencies = [
    # Core
    "litellm>=1.0.0",
    "jupyter-client>=8.0.0",
    "ipykernel>=6.0.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
    # CLI
    "rich>=13.0.0",
    "prompt-toolkit>=3.0.0",
    # Data Science
    "pandas>=2.0.0",
    "numpy>=1.24.0",
]

[project.optional-dependencies]
api = [
    "fastapi>=0.100.0",
    "uvicorn>=0.20.0",
    "sse-starlette>=1.0.0",
    "websockets>=12.0",
    "python-multipart>=0.0.6",  # File uploads
]
db = [
    "asyncpg>=0.28.0",          # PostgreSQL
    "redis>=5.0.0",             # Redis
    "alembic>=1.12.0",          # Migrations
    "sqlalchemy>=2.0.0",        # ORM
]
storage = [
    "boto3>=1.28.0",            # AWS S3
    "google-cloud-storage>=2.10.0",  # GCS
    "azure-storage-blob>=12.0.0",    # Azure
]
all = [
    "datascience-agent[api,db,storage]",
]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "httpx>=0.25.0",            # API testing
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]
```
