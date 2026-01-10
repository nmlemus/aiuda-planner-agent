"""FastAPI Dependencies for DSAgent Server."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING, Optional

from fastapi import Depends, Header, HTTPException, Query, status
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from dsagent.server.manager import AgentConnectionManager
    from dsagent.session import SessionManager

# Global instances (set by app.py on startup)
_connection_manager: Optional["AgentConnectionManager"] = None
_session_manager: Optional["SessionManager"] = None


class ServerSettings(BaseSettings):
    """Server configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="DSAGENT_",
    )

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    # Authentication
    api_key: Optional[str] = None  # If set, API key auth is enabled

    # CORS settings
    cors_origins: str = "*"  # Comma-separated origins or "*" for all

    # Agent defaults
    default_model: Optional[str] = None
    default_hitl_mode: str = "none"

    # Session storage
    session_backend: str = "sqlite"  # "sqlite" or "json"
    sessions_dir: str = "runs"


@lru_cache
def get_settings() -> ServerSettings:
    """Get cached server settings."""
    return ServerSettings()


def set_connection_manager(manager: "AgentConnectionManager") -> None:
    """Set the global connection manager (called on startup)."""
    global _connection_manager
    _connection_manager = manager


def set_session_manager(manager: "SessionManager") -> None:
    """Set the global session manager (called on startup)."""
    global _session_manager
    _session_manager = manager


def get_connection_manager() -> "AgentConnectionManager":
    """Get the connection manager.

    Raises:
        HTTPException: If manager not initialized
    """
    if _connection_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server not fully initialized",
        )
    return _connection_manager


def get_session_manager() -> "SessionManager":
    """Get the session manager.

    Raises:
        HTTPException: If manager not initialized
    """
    if _session_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server not fully initialized",
        )
    return _session_manager


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    settings: ServerSettings = Depends(get_settings),
) -> Optional[str]:
    """Verify API key if authentication is enabled.

    Args:
        x_api_key: API key from header
        settings: Server settings

    Returns:
        The API key if valid

    Raises:
        HTTPException: If authentication fails
    """
    # If no API key configured, auth is disabled (dev mode)
    if not settings.api_key:
        return None

    # API key required but not provided
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Verify API key
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key


async def verify_websocket_api_key(
    api_key: Optional[str] = Query(None),
    settings: ServerSettings = Depends(get_settings),
) -> Optional[str]:
    """Verify API key for WebSocket connections (via query param).

    Args:
        api_key: API key from query parameter
        settings: Server settings

    Returns:
        The API key if valid

    Raises:
        HTTPException: If authentication fails
    """
    # If no API key configured, auth is disabled (dev mode)
    if not settings.api_key:
        return None

    # API key required but not provided
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required (pass as ?api_key=xxx)",
        )

    # Verify API key
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return api_key
