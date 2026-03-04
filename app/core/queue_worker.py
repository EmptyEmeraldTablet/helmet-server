import asyncio
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.broadcast import ConnectionManager
from app.core.inference import get_engine
from app.models import Alert, Detection, Task


@dataclass
class TaskItem:
    task_id: str
    image_path: str
    event: asyncio.Event


class TaskQueue:
    def __init__(self, maxsize: int) -> None:
        self.queue: asyncio.Queue[TaskItem] = asyncio.Queue(maxsize=maxsize)

    async def put(self, item: TaskItem) -> None:
        await self.queue.put(item)

    async def get(self) -> TaskItem:
        return await self.queue.get()

    def task_done(self) -> None:
        self.queue.task_done()


async def worker_loop(task_queue: TaskQueue, session_factory, broadcaster: ConnectionManager | None) -> None:
    while True:
        task_item = await task_queue.get()
        async with session_factory() as session:
            await process_task(session, task_item, broadcaster)
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
    try:
        engine = get_engine()
        detections, elapsed_ms, annotated_path = engine.predict(task_item.image_path)
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
        await session.commit()

    if broadcaster and task.status == "completed":
        payload = {
            "event": "new_result",
            "data": {
                "task_id": task.id,
                "device_id": task.device_id,
                "created_at": task.created_at.isoformat() + "Z",
                "original_image_url": task.original_image_path,
                "annotated_image_url": task.annotated_image_path,
                "detections": detections,
                "has_violation": task.has_violation,
            },
        }
        await broadcaster.broadcast(payload)

        if task.has_violation:
            alert_payload = {
                "event": "alert",
                "data": {
                    "task_id": task.id,
                    "device_id": task.device_id,
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "annotated_image_url": task.annotated_image_path,
                    "violation_count": violation_count,
                },
            }
            await broadcaster.broadcast(alert_payload)
