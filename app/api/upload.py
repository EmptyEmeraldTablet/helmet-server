import asyncio
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.queue_worker import TaskItem, TaskQueue
from app.db.database import get_db_session
from app.models import Task
from app.schemas.common import ApiResponse
from app.schemas.upload import Detection, UploadResponseData
from app.utils.image import save_upload_file

router = APIRouter()

_queue: TaskQueue | None = None


def set_queue(queue: TaskQueue) -> None:
    global _queue
    _queue = queue


def get_queue() -> TaskQueue:
    if _queue is None:
        raise RuntimeError("Queue not initialized")
    return _queue


@router.post("/upload", response_model=ApiResponse[UploadResponseData])
async def upload_image(
    file: UploadFile = File(...),
    device_id: str = Form(...),
    session: AsyncSession = Depends(get_db_session),
    queue: TaskQueue = Depends(get_queue),
) -> ApiResponse[UploadResponseData]:
    if queue.queue.full():
        raise HTTPException(status_code=503, detail="Queue full")

    if file.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(status_code=400, detail="Invalid image format")

    image_path = await save_upload_file(file)

    task = Task(
        id=str(uuid4()),
        device_id=device_id,
        status="pending",
        original_image_path=image_path,
        created_at=datetime.utcnow(),
    )
    session.add(task)
    await session.commit()

    event = asyncio.Event()
    await queue.put(TaskItem(task_id=task.id, image_path=image_path, event=event))
    await event.wait()

    await session.refresh(task)

    detections = [
        Detection(
            label=d.label,
            confidence=d.confidence,
            bbox=[d.bbox_x1, d.bbox_y1, d.bbox_x2, d.bbox_y2],
        )
        for d in task.detections
    ]

    data = UploadResponseData(
        task_id=task.id,
        status=task.status,
        annotated_image_url=task.annotated_image_path,
        detections=detections,
        has_violation=task.has_violation,
        process_time_ms=task.process_time_ms,
    )

    return ApiResponse(code=0, message="success", data=data)
