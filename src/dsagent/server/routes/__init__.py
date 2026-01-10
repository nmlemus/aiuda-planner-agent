"""API Routes for DSAgent Server."""

from dsagent.server.routes.chat import router as chat_router
from dsagent.server.routes.health import router as health_router
from dsagent.server.routes.kernel import router as kernel_router
from dsagent.server.routes.sessions import router as sessions_router

__all__ = [
    "chat_router",
    "health_router",
    "kernel_router",
    "sessions_router",
]
