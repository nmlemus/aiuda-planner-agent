#!/usr/bin/env python3
"""FastAPI integration example for the Aiuda Planner Agent.

This example demonstrates:
1. Creating a REST API for the agent
2. Server-Sent Events (SSE) streaming
3. Session management for multiple users

Run with:
    pip install "aiuda-planner-agent[api]"
    uvicorn fastapi_example:app --reload

Test with:
    curl -X POST "http://localhost:8000/analyze" \
         -H "Content-Type: application/json" \
         -d '{"task": "Analyze data and find trends"}'
"""

import os
import asyncio
from uuid import uuid4
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from datapilot import PlannerAgent, EventType

# Create FastAPI app
app = FastAPI(
    title="Aiuda Planner Agent API",
    description="REST API for the AI Planner Agent",
    version="0.1.0",
)

# Store active sessions
active_sessions: dict[str, PlannerAgent] = {}


class AnalyzeRequest(BaseModel):
    """Request model for analysis."""
    task: str
    model: str = "gpt-4o"
    session_id: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """Response model for synchronous analysis."""
    answer: str
    notebook_path: Optional[str]
    rounds: int
    success: bool


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze_sync(request: AnalyzeRequest):
    """Run analysis synchronously and return result."""
    workspace = Path(f"./workspaces/{request.session_id or uuid4()}")
    workspace.mkdir(parents=True, exist_ok=True)

    with PlannerAgent(
        model=request.model,
        workspace=workspace,
        session_id=request.session_id,
        verbose=False,
    ) as agent:
        result = agent.run(request.task)

    return AnalyzeResponse(
        answer=result.answer,
        notebook_path=str(result.notebook_path) if result.notebook_path else None,
        rounds=result.rounds,
        success=result.success,
    )


@app.post("/analyze/stream")
async def analyze_stream(request: AnalyzeRequest):
    """Run analysis with Server-Sent Events streaming."""

    async def event_generator():
        session_id = request.session_id or str(uuid4())
        workspace = Path(f"./workspaces/{session_id}")
        workspace.mkdir(parents=True, exist_ok=True)

        agent = PlannerAgent(
            model=request.model,
            workspace=workspace,
            session_id=session_id,
            verbose=False,
        )
        agent.start()
        active_sessions[session_id] = agent

        try:
            for event in agent.run_stream(request.task):
                # Convert event to SSE format
                sse_data = event.to_sse()
                yield f"data: {sse_data}\n\n"

                # Small delay to prevent overwhelming the client
                await asyncio.sleep(0.01)

            # Generate notebook and send final result
            result = agent.get_result()
            final_data = {
                "type": "result",
                "answer": result.answer,
                "notebook_path": str(result.notebook_path) if result.notebook_path else None,
                "rounds": result.rounds,
                "success": result.success,
            }
            import json
            yield f"data: {json.dumps(final_data)}\n\n"

        finally:
            agent.shutdown()
            active_sessions.pop(session_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.get("/sessions/{session_id}/state")
async def get_session_state(session_id: str):
    """Get state of an active session."""
    agent = active_sessions.get(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"state": agent.serialize_state()}


@app.delete("/sessions/{session_id}")
async def stop_session(session_id: str):
    """Stop an active session."""
    agent = active_sessions.pop(session_id, None)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found")

    agent.shutdown()
    return {"status": "stopped", "session_id": session_id}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
