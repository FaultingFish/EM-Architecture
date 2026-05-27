"""WebSocket telemetry endpoint."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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
    await socket.accept()
    try:
        await socket.send_json({"type": "ok", "detail": "WS scaffold — see routers/ws.py"})
        # TODO: bind to control.state.Broadcaster
        while True:
            msg = await socket.receive_json()
            await socket.send_json({"type": "error", "id": msg.get("id"), "error": "not implemented"})
    except WebSocketDisconnect:
        pass
