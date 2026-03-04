from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db_session
from app.dependencies import get_current_admin
from app.models import Detection as DetectionModel
from app.models import Task
from app.schemas.common import ApiResponse
from app.schemas.result import ResultDetail, ResultItem, ResultListResponse
from app.schemas.upload import Detection
from app.utils.image import build_storage_url

router = APIRouter()


def parse_iso_datetime(value: str | None, field_name: str) -> datetime | None:
    if value is None:
        return None
    normalized = value
    if value.endswith("Z"):
        normalized = f"{value[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}") from exc
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def build_detection_response(detection: DetectionModel) -> Detection:
    return Detection(
        label=detection.label,
        confidence=detection.confidence,
        bbox=[
            detection.bbox_x1,
            detection.bbox_y1,
            detection.bbox_x2,
            detection.bbox_y2,
        ],
    )


@router.get("/results", response_model=ApiResponse[ResultListResponse])
async def list_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    device_id: str | None = Query(None),
    has_violation: bool | None = Query(None),
    start_time: str | None = Query(None),
    end_time: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(get_current_admin),
) -> ApiResponse[ResultListResponse]:
    start_dt = parse_iso_datetime(start_time, "start_time")
    end_dt = parse_iso_datetime(end_time, "end_time")

    filters: list = []
    if device_id:
        filters.append(Task.device_id == device_id)
    if has_violation is not None:
        filters.append(Task.has_violation.is_(has_violation))
    if start_dt:
        filters.append(Task.created_at >= start_dt)
    if end_dt:
        filters.append(Task.created_at <= end_dt)

    total_query = select(func.count()).select_from(Task)
    if filters:
        total_query = total_query.where(*filters)
    total = await session.scalar(total_query)

    query = select(Task).options(selectinload(Task.detections))
    if filters:
        query = query.where(*filters)
    query = query.order_by(Task.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    tasks = result.scalars().all()

    items = [
        ResultItem(
            task_id=task.id,
            device_id=task.device_id,
            created_at=task.created_at,
            annotated_image_url=build_storage_url(task.annotated_image_path),
            detections=[build_detection_response(detection) for detection in task.detections],
            has_violation=task.has_violation,
        )
        for task in tasks
    ]

    data = ResultListResponse(total=total or 0, items=items)
    return ApiResponse(code=0, message="success", data=data)


@router.get("/results/{task_id}", response_model=ApiResponse[ResultDetail])
async def get_result_detail(
    task_id: str,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(get_current_admin),
) -> ApiResponse[ResultDetail]:
    result = await session.execute(
        select(Task).options(selectinload(Task.detections)).where(Task.id == task_id)
    )
    task = result.scalars().first()
    if task is None:
        raise HTTPException(status_code=404, detail="Result not found")

    data = ResultDetail(
        task_id=task.id,
        device_id=task.device_id,
        created_at=task.created_at,
        annotated_image_url=build_storage_url(task.annotated_image_path),
        detections=[build_detection_response(detection) for detection in task.detections],
        has_violation=task.has_violation,
        original_image_url=build_storage_url(task.original_image_path),
        process_time_ms=task.process_time_ms,
    )
    return ApiResponse(code=0, message="success", data=data)
