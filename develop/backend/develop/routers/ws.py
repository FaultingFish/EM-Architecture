"""WebSocket for build-log + agent-output streaming."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["ws"])


@router.websocket("/ws")
async def ws(socket: WebSocket) -> None:
    """Subscribe to:
    - build_log     — per-line stdout/stderr from running builds
    - build_status  — phase transitions
    - agent_output  — per-line output from `claude` subprocess

    TODO: maintain per-project subscription so multiple builds don't cross.
    """
    await socket.accept()
    try:
        await socket.send_json({"type": "ok", "detail": "WS scaffold — see routers/ws.py"})
        while True:
            msg = await socket.receive_json()
            await socket.send_json({"type": "error", "id": msg.get("id"), "error": "not implemented"})
    except WebSocketDisconnect:
        pass
