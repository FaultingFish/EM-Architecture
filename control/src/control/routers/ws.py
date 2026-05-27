"""WebSocket telemetry endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["ws"])


@router.websocket("/ws")
async def ws(socket: WebSocket) -> None:
    """Stream live telemetry to the client.

    On connect, the server sends a full `state` snapshot. After that, every
    AppState mutation produces an event with one of the topics listed in
    emfi_protocol.WsTopic.

    TODO:
    1. Accept the connection, register a queue with the Broadcaster.
    2. Send the initial state snapshot.
    3. Loop: pull from the queue and send_json(); handle disconnect.
    """
    client = f"{socket.client.host}:{socket.client.port}" if socket.client else "unknown"
    LOGGER.info("WS connect from %s", client)
    await socket.accept()
    try:
        await socket.send_json({"type": "ok", "detail": "WS scaffold — see routers/ws.py"})
        # TODO: bind to control.state.Broadcaster
        while True:
            msg = await socket.receive_json()
            LOGGER.debug("WS recv from %s: %s", client, msg.get("action", msg))
            await socket.send_json({"type": "error", "id": msg.get("id"), "error": "not implemented"})
    except WebSocketDisconnect:
        LOGGER.info("WS disconnect from %s", client)
