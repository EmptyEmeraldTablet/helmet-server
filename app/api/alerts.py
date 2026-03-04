from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.dependencies import get_current_admin
from app.models import Alert
from app.schemas.alert import AlertListResponse, AlertResponse
from app.schemas.common import ApiResponse

router = APIRouter()


@router.get("/alerts", response_model=ApiResponse[AlertListResponse])
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(get_current_admin),
) -> ApiResponse[AlertListResponse]:
    total = await session.scalar(select(func.count()).select_from(Alert))
    result = await session.execute(
        select(Alert)
        .order_by(Alert.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    alerts = result.scalars().all()

    data = AlertListResponse(
        total=total or 0,
        items=[
            AlertResponse(
                id=alert.id,
                task_id=alert.task_id,
                device_id=alert.device_id,
                violation_count=alert.violation_count,
                is_read=alert.is_read,
                created_at=alert.created_at,
            )
            for alert in alerts
        ],
    )
    return ApiResponse(code=0, message="success", data=data)


@router.put("/alerts/{alert_id}/read", response_model=ApiResponse[AlertResponse])
async def mark_alert_read(
    alert_id: str,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(get_current_admin),
) -> ApiResponse[AlertResponse]:
    alert = await session.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.is_read = True
    await session.commit()

    data = AlertResponse(
        id=alert.id,
        task_id=alert.task_id,
        device_id=alert.device_id,
        violation_count=alert.violation_count,
        is_read=alert.is_read,
        created_at=alert.created_at,
    )
    return ApiResponse(code=0, message="success", data=data)


@router.put("/alerts/read-all", response_model=ApiResponse[dict])
async def mark_all_read(
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(get_current_admin),
) -> ApiResponse[dict]:
    result = await session.execute(select(Alert).where(Alert.is_read.is_(False)))
    alerts = result.scalars().all()
    for alert in alerts:
        alert.is_read = True
    await session.commit()

    return ApiResponse(code=0, message="success", data={"updated": len(alerts)})
