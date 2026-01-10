"""WebSocket endpoint for real-time chat."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from dsagent.server.deps import (
    get_connection_manager,
    get_settings,
    ServerSettings,
)
from dsagent.server.manager import AgentConnectionManager
from dsagent.server.models import (
    WebSocketEvent,
    WebSocketMessage,
    WebSocketMessageType,
)

logger = logging.getLogger(__name__)
router = APIRouter()


async def verify_websocket_auth(
    websocket: WebSocket,
    api_key: Optional[str],
    settings: ServerSettings,
) -> bool:
    """Verify API key for WebSocket connection.

    Args:
        websocket: WebSocket connection
        api_key: API key from query parameter
        settings: Server settings

    Returns:
        True if authenticated, False otherwise
    """
    # If no API key configured, auth is disabled
    if not settings.api_key:
        return True

    # Verify API key
    if api_key != settings.api_key:
        await websocket.close(code=4001, reason="Invalid or missing API key")
        return False

    return True


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(
    websocket: WebSocket,
    session_id: str,
    api_key: Optional[str] = Query(None),
    model: Optional[str] = Query(None),
    hitl_mode: Optional[str] = Query(None),
):
    """WebSocket endpoint for real-time chat.

    Connect to: ws://host/ws/chat/{session_id}?api_key=xxx

    Message format (client -> server):
    ```json
    {
        "type": "chat",
        "content": "Your message here"
    }
    ```

    Event format (server -> client):
    ```json
    {
        "type": "response",
        "data": {...},
        "timestamp": "2024-01-01T00:00:00Z",
        "session_id": "xxx"
    }
    ```

    Event types:
    - connected: Connection established
    - thinking: Agent is processing
    - plan: Plan received/updated
    - code_executing: Code is being executed
    - code_result: Code execution result
    - response: Agent response (partial or complete)
    - answer: Final answer
    - error: Error occurred
    - complete: Task completed
    - disconnected: Connection closed
    """
    settings = get_settings()
    connection_manager = get_connection_manager()

    # Verify authentication
    if not await verify_websocket_auth(websocket, api_key, settings):
        return

    try:
        # Connect and get agent
        agent = await connection_manager.connect(
            websocket,
            session_id,
            model=model,
            hitl_mode=hitl_mode,
        )

        # Send connected event
        await connection_manager.send_to(
            websocket,
            WebSocketEvent.connected(session_id, f"Connected to session {session_id}"),
        )

        # Message handling loop
        while True:
            try:
                # Receive message
                raw_data = await websocket.receive_text()
                data = json.loads(raw_data)

                # Parse message
                try:
                    message = WebSocketMessage(**data)
                except Exception as e:
                    await connection_manager.send_to(
                        websocket,
                        WebSocketEvent.error(session_id, f"Invalid message format: {e}"),
                    )
                    continue

                # Handle message based on type
                if message.type == WebSocketMessageType.CHAT:
                    if not message.content:
                        await connection_manager.send_to(
                            websocket,
                            WebSocketEvent.error(session_id, "Message content is required"),
                        )
                        continue

                    # Process chat message
                    await connection_manager.chat(
                        session_id,
                        message.content,
                        websocket=websocket,
                    )

                elif message.type == WebSocketMessageType.EXECUTE:
                    if not message.code:
                        await connection_manager.send_to(
                            websocket,
                            WebSocketEvent.error(session_id, "Code is required"),
                        )
                        continue

                    # Execute code directly
                    try:
                        result = await connection_manager.execute_code(
                            session_id,
                            message.code,
                        )
                        await connection_manager.send_to(
                            websocket,
                            WebSocketEvent.code_result(session_id, result),
                        )
                    except Exception as e:
                        await connection_manager.send_to(
                            websocket,
                            WebSocketEvent.error(session_id, str(e), message.code),
                        )

                elif message.type == WebSocketMessageType.APPROVE:
                    # Handle HITL approval
                    # TODO: Implement HITL approval flow
                    await connection_manager.send_to(
                        websocket,
                        WebSocketEvent.response(
                            session_id,
                            f"Approval received: {message.approved}",
                        ),
                    )

                elif message.type == WebSocketMessageType.CANCEL:
                    # Handle cancellation
                    # TODO: Implement task cancellation
                    await connection_manager.send_to(
                        websocket,
                        WebSocketEvent.response(session_id, "Cancellation not yet implemented"),
                    )

                else:
                    await connection_manager.send_to(
                        websocket,
                        WebSocketEvent.error(session_id, f"Unknown message type: {message.type}"),
                    )

            except json.JSONDecodeError as e:
                await connection_manager.send_to(
                    websocket,
                    WebSocketEvent.error(session_id, f"Invalid JSON: {e}"),
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected from session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        try:
            await connection_manager.send_to(
                websocket,
                WebSocketEvent.error(session_id, f"Server error: {e}"),
            )
        except Exception:
            pass
    finally:
        await connection_manager.disconnect(websocket, session_id)
