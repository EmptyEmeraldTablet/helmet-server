import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.broadcast import ConnectionManager
from app.core.queue_worker import TaskItem, TaskQueue
from app.db.database import get_db_session
from app.models import Device, StreamFrame, StreamSession, Task
from app.utils.image import save_base64_image
from app.utils.security import decode_token

router = APIRouter()

_manager: ConnectionManager | None = None
_stream_queue: TaskQueue | None = None


def set_manager(manager: ConnectionManager) -> None:
    global _manager
    _manager = manager


def get_manager() -> ConnectionManager:
    if _manager is None:
        raise RuntimeError("WebSocket manager not initialized")
    return _manager


def set_stream_queue(queue: TaskQueue) -> None:
    global _stream_queue
    _stream_queue = queue


def get_stream_queue() -> TaskQueue:
    if _stream_queue is None:
        raise RuntimeError("Stream queue not initialized")
    return _stream_queue


def parse_iso_timestamp(value: str) -> datetime | None:
    normalized = value
    if value.endswith("Z"):
        normalized = f"{value[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


async def send_error(
    websocket: WebSocket,
    code: str,
    message: str,
    stream_id: str | None = None,
    frame_index: int | None = None,
) -> None:
    payload = {
        "event": "error",
        "data": {
            "code": code,
            "message": message,
            "stream_id": stream_id,
            "frame_index": frame_index,
        },
    }
    await websocket.send_json(payload)


async def mark_dropped(
    session: AsyncSession, dropped: TaskItem
) -> int | None:
    task = await session.get(Task, dropped.task_id)
    frame_index = None
    if task:
        task.status = "dropped"
        task.error_message = "Dropped due to queue pressure"
        task.completed_at = datetime.utcnow()
        if task.original_image_path:
            Path(task.original_image_path).unlink(missing_ok=True)
            task.original_image_path = None
        if task.annotated_image_path:
            Path(task.annotated_image_path).unlink(missing_ok=True)
            task.annotated_image_path = None
    if dropped.frame_id:
        frame = await session.get(StreamFrame, dropped.frame_id)
        if frame:
            frame.status = "dropped"
            frame_index = frame.frame_index
            if frame.image_path:
                Path(frame.image_path).unlink(missing_ok=True)
                frame.image_path = None
    await session.commit()
    return frame_index


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


@router.websocket("/ws/stream")
async def stream_ws(
    websocket: WebSocket,
    session: AsyncSession = Depends(get_db_session),
    queue: TaskQueue = Depends(get_stream_queue),
) -> None:
    token = websocket.query_params.get("token")
    if not token or not decode_token(token):
        await websocket.close(code=1008)
        return

    manager = get_manager()
    await manager.connect(websocket)
    active_streams: dict[str, str] = {}

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                await send_error(websocket, "invalid_payload", "Invalid JSON")
                continue

            msg_type = payload.get("type")
            data = payload.get("data") or {}

            if msg_type == "start":
                device_id = data.get("device_id")
                stream_id = data.get("stream_id")
                fps = data.get("fps")
                resolution = data.get("resolution")
                source = data.get("source")

                if not device_id or not stream_id or not fps or not resolution:
                    await send_error(websocket, "invalid_payload", "Missing start fields")
                    continue

                if stream_id in active_streams:
                    await send_error(websocket, "invalid_payload", "Stream already active", stream_id)
                    continue

                device = await session.get(Device, device_id)
                if device is None or device.status != "active":
                    await send_error(websocket, "invalid_payload", "Device not active", stream_id)
                    continue

                existing = await session.get(StreamSession, stream_id)
                if existing and existing.status == "active":
                    await send_error(websocket, "invalid_payload", "Stream id in use", stream_id)
                    continue

                stream_session = StreamSession(
                    id=stream_id,
                    device_id=device_id,
                    status="active",
                    fps_target=int(fps),
                    resolution=str(resolution),
                    source=source,
                    started_at=datetime.utcnow(),
                )
                session.add(stream_session)
                device.last_seen_at = datetime.utcnow()
                await session.commit()

                active_streams[stream_id] = device_id
                await websocket.send_json(
                    {
                        "event": "ack",
                        "data": {"stream_id": stream_id, "status": "accepted"},
                    }
                )
                continue

            if msg_type == "frame":
                stream_id = data.get("stream_id")
                frame_index = data.get("frame_index")
                timestamp = data.get("timestamp")
                image_base64 = data.get("image_base64")

                if not stream_id or frame_index is None or not timestamp or not image_base64:
                    await send_error(websocket, "invalid_payload", "Missing frame fields")
                    continue

                if stream_id not in active_streams:
                    await send_error(websocket, "stream_not_found", "Stream not active", stream_id)
                    continue

                captured_at = parse_iso_timestamp(str(timestamp))
                if captured_at is None:
                    await send_error(websocket, "invalid_payload", "Invalid timestamp", stream_id)
                    continue

                if queue.queue.full():
                    dropped = queue.drop_oldest()
                    if dropped:
                        dropped_index = await mark_dropped(session, dropped)
                        await send_error(
                            websocket,
                            "queue_full",
                            "Frame dropped due to queue pressure",
                            stream_id,
                            dropped_index,
                        )

                image_path = None
                try:
                    image_path = save_base64_image(image_base64)
                except ValueError:
                    await send_error(websocket, "invalid_payload", "Invalid image payload", stream_id)
                    continue

                frame_id = str(uuid4())
                frame = StreamFrame(
                    id=frame_id,
                    session_id=stream_id,
                    frame_index=int(frame_index),
                    captured_at=captured_at,
                    received_at=datetime.utcnow(),
                    image_path=image_path,
                    status="queued",
                )
                task = Task(
                    id=str(uuid4()),
                    device_id=active_streams[stream_id],
                    status="pending",
                    original_image_path=image_path,
                    created_at=datetime.utcnow(),
                    session_id=stream_id,
                    frame_id=frame_id,
                )
                session.add(frame)
                session.add(task)
                await session.commit()

                accepted = queue.put_nowait(
                    TaskItem(
                        task_id=task.id,
                        image_path=image_path,
                        event=None,
                        frame_id=frame_id,
                    )
                )
                if not accepted:
                    frame.status = "dropped"
                    if frame.image_path:
                        Path(frame.image_path).unlink(missing_ok=True)
                        frame.image_path = None
                    task.status = "dropped"
                    task.error_message = "Dropped due to queue pressure"
                    await session.commit()
                    await send_error(
                        websocket,
                        "queue_full",
                        "Frame dropped due to queue pressure",
                        stream_id,
                        int(frame_index),
                    )
                    continue

                await websocket.send_json(
                    {
                        "event": "ack",
                        "data": {
                            "stream_id": stream_id,
                            "frame_index": int(frame_index),
                            "status": "accepted",
                        },
                    }
                )
                continue

            if msg_type == "stop":
                stream_id = data.get("stream_id")
                if not stream_id:
                    await send_error(websocket, "invalid_payload", "Missing stream_id")
                    continue

                if stream_id in active_streams:
                    stream = await session.get(StreamSession, stream_id)
                    if stream:
                        stream.status = "closed"
                        stream.ended_at = datetime.utcnow()
                        await session.commit()
                    active_streams.pop(stream_id, None)

                await websocket.send_json(
                    {
                        "event": "ack",
                        "data": {"stream_id": stream_id, "status": "accepted"},
                    }
                )
                continue

            await send_error(websocket, "invalid_payload", "Unknown message type")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    finally:
        for stream_id in list(active_streams.keys()):
            stream = await session.get(StreamSession, stream_id)
            if stream and stream.status == "active":
                stream.status = "closed"
                stream.ended_at = datetime.utcnow()
        await session.commit()
