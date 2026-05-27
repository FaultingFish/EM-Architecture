"""WebSocket for build-log + agent-output streaming."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

log = logging.getLogger(__name__)

router = APIRouter(tags=["ws"])


@router.websocket("/ws")
async def ws(socket: WebSocket) -> None:
    """Subscribe to:
    - build_log     — per-line stdout/stderr from running builds
    - build_status  — phase transitions
    - agent_output  — per-line output from `claude` subprocess

    TODO: maintain per-project subscription so multiple builds don't cross.
    """
    client = f"{socket.client.host}:{socket.client.port}" if socket.client else "unknown"
    log.info("WS connect from %s", client)
    await socket.accept()
    try:
        await socket.send_json({"type": "ok", "detail": "WS scaffold — see routers/ws.py"})
        while True:
            msg = await socket.receive_json()
            log.debug("WS recv from %s: %s", client, msg)
            await socket.send_json({"type": "error", "id": msg.get("id"), "error": "not implemented"})
    except WebSocketDisconnect:
        log.info("WS disconnect from %s", client)
