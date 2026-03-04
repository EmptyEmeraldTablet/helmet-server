from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.dependencies import get_current_admin
from app.models import Device, Task
from app.schemas.common import ApiResponse
from app.schemas.stats import DeviceStats, DeviceStatsResponse, SummaryStats, TrendPoint, TrendResponse

router = APIRouter()


@router.get("/stats/summary", response_model=ApiResponse[SummaryStats])
async def summary_stats(
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(get_current_admin),
) -> ApiResponse[SummaryStats]:
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    total_today = await session.scalar(
        select(func.count()).select_from(Task).where(Task.created_at >= start, Task.created_at < end)
    )
    violations_today = await session.scalar(
        select(func.count())
        .select_from(Task)
        .where(Task.created_at >= start, Task.created_at < end, Task.has_violation.is_(True))
    )
    active_devices = await session.scalar(
        select(func.count()).select_from(Device).where(Device.status == "active")
    )

    total_today = total_today or 0
    violations_today = violations_today or 0
    violation_rate = (violations_today / total_today) if total_today else 0.0

    data = SummaryStats(
        total_today=total_today,
        violations_today=violations_today,
        violation_rate=violation_rate,
        active_devices=active_devices or 0,
    )
    return ApiResponse(code=0, message="success", data=data)


@router.get("/stats/trend", response_model=ApiResponse[TrendResponse])
async def trend_stats(
    granularity: str = Query("day"),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    device_id: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(get_current_admin),
) -> ApiResponse[TrendResponse]:
    if granularity not in {"hour", "day", "week"}:
        raise HTTPException(status_code=400, detail="Invalid granularity")

    if end_time is None:
        end_time = datetime.utcnow()
    if start_time is None:
        start_time = end_time - timedelta(days=7)

    if granularity == "hour":
        bucket = func.strftime("%Y-%m-%d %H:00:00", Task.created_at)
    elif granularity == "week":
        bucket = func.strftime("%Y-W%W", Task.created_at)
    else:
        bucket = func.strftime("%Y-%m-%d", Task.created_at)

    query = (
        select(bucket.label("bucket"), func.count().label("count"))
        .select_from(Task)
        .where(Task.created_at >= start_time, Task.created_at <= end_time)
        .group_by("bucket")
        .order_by("bucket")
    )
    if device_id:
        query = query.where(Task.device_id == device_id)

    result = await session.execute(query)
    points = [TrendPoint(bucket=row.bucket, count=row.count) for row in result.all()]

    return ApiResponse(code=0, message="success", data=TrendResponse(granularity=granularity, points=points))


@router.get("/stats/devices", response_model=ApiResponse[DeviceStatsResponse])
async def device_stats(
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(get_current_admin),
) -> ApiResponse[DeviceStatsResponse]:
    result = await session.execute(
        select(Task.device_id.label("device_id"), func.count().label("count"))
        .group_by(Task.device_id)
        .order_by(func.count().desc())
    )
    items = [DeviceStats(device_id=row.device_id, count=row.count) for row in result.all()]
    return ApiResponse(code=0, message="success", data=DeviceStatsResponse(items=items))
