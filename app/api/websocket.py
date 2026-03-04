from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.broadcast import ConnectionManager
from app.utils.security import decode_token

router = APIRouter()

_manager: ConnectionManager | None = None


def set_manager(manager: ConnectionManager) -> None:
    global _manager
    _manager = manager


def get_manager() -> ConnectionManager:
    if _manager is None:
        raise RuntimeError("WebSocket manager not initialized")
    return _manager


@router.websocket("/ws/monitor")
async def monitor_ws(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    if not token or not decode_token(token):
        await websocket.close(code=1008)
        return

    manager = get_manager()
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
