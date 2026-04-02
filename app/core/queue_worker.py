import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.broadcast import ConnectionManager
from app.config import settings
from app.core.inference import get_engine
from app.models import Alert, Detection, StreamFrame, Task
from app.utils.image import build_storage_url


@dataclass
class TaskItem:
    task_id: str
    image_path: str
    event: asyncio.Event | None = None
    frame_id: str | None = None


class TaskQueue:
    def __init__(self, maxsize: int) -> None:
        self.queue: asyncio.Queue[TaskItem] = asyncio.Queue(maxsize=maxsize)

    async def put(self, item: TaskItem) -> None:
        await self.queue.put(item)

    def put_nowait(self, item: TaskItem) -> bool:
        try:
            self.queue.put_nowait(item)
        except asyncio.QueueFull:
            return False
        return True

    async def get(self) -> TaskItem:
        return await self.queue.get()

    def task_done(self) -> None:
        self.queue.task_done()

    def drop_oldest(self) -> TaskItem | None:
        try:
            item = self.queue.get_nowait()
        except asyncio.QueueEmpty:
            return None
        self.queue.task_done()
        return item


async def worker_loop(task_queue: TaskQueue, session_factory, broadcaster: ConnectionManager | None) -> None:
    while True:
        task_item = await task_queue.get()
        async with session_factory() as session:
            await process_task(session, task_item, broadcaster)
        if task_item.event:
            task_item.event.set()
        task_queue.task_done()


async def process_task(
    session: AsyncSession, task_item: TaskItem, broadcaster: ConnectionManager | None
) -> None:
    task = await session.get(Task, task_item.task_id)
    if task is None:
        return

    task.status = "processing"
    await session.commit()

    detections: list[dict] = []
    violation_count = 0
    frame: StreamFrame | None = None
    if task.frame_id:
        frame = await session.get(StreamFrame, task.frame_id)
    try:
        if not task.original_image_path:
            raise RuntimeError("Missing image path")
        engine = get_engine()
        detections, elapsed_ms, annotated_path = engine.predict(task.original_image_path)
        task.status = "completed"
        task.process_time_ms = int(elapsed_ms)
        task.annotated_image_path = annotated_path
        task.completed_at = datetime.utcnow()
        task.has_violation = any(d["label"] == "no_helmet" for d in detections)

        for detection in detections:
            bbox = detection["bbox"]
            session.add(
                Detection(
                    task_id=task.id,
                    label=detection["label"],
                    confidence=detection["confidence"],
                    bbox_x1=bbox[0],
                    bbox_y1=bbox[1],
                    bbox_x2=bbox[2],
                    bbox_y2=bbox[3],
                )
            )

        violation_count = sum(1 for d in detections if d["label"] == "no_helmet")
        if violation_count > 0:
            alert = Alert(
                task_id=task.id,
                device_id=task.device_id,
                violation_count=violation_count,
            )
            session.add(alert)
    except Exception as exc:  # noqa: BLE001
        task.status = "failed"
        task.error_message = str(exc)
        task.completed_at = datetime.utcnow()
    finally:
        if frame:
            frame.status = "processed" if task.status == "completed" else "dropped"
        await session.commit()

    if (
        frame
        and task.status == "completed"
        and not task.has_violation
        and not settings.preserve_stream_data
    ):
        if task.original_image_path:
            Path(task.original_image_path).unlink(missing_ok=True)
            task.original_image_path = None
        if task.annotated_image_path:
            Path(task.annotated_image_path).unlink(missing_ok=True)
            task.annotated_image_path = None
        frame.image_path = None
        await session.commit()

    if broadcaster and task.status == "completed":
        latency_ms = None
        frame_index = None
        stream_id = None
        if frame:
            frame_index = frame.frame_index
            stream_id = frame.session_id
            if frame.captured_at:
                latency_ms = int((datetime.utcnow() - frame.captured_at).total_seconds() * 1000)
        payload = {
            "event": "new_result",
            "data": {
                "stream_id": stream_id,
                "frame_index": frame_index,
                "task_id": task.id,
                "device_id": task.device_id,
                "created_at": task.created_at.isoformat() + "Z",
                "original_image_url": build_storage_url(task.original_image_path),
                "annotated_image_url": build_storage_url(task.annotated_image_path),
                "detections": detections,
                "has_violation": task.has_violation,
                "latency_ms": latency_ms,
            },
        }
        await broadcaster.broadcast(payload)

        if task.has_violation:
            alert_payload = {
                "event": "alert",
                "data": {
                    "stream_id": stream_id,
                    "frame_index": frame_index,
                    "task_id": task.id,
                    "device_id": task.device_id,
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "annotated_image_url": build_storage_url(task.annotated_image_path),
                    "violation_count": violation_count,
                },
            }
            await broadcaster.broadcast(alert_payload)
