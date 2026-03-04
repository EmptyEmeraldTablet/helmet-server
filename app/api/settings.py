import json
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.db.database import get_db_session
from app.dependencies import get_current_admin
from app.models import SystemConfig
from app.schemas.common import ApiResponse
from app.schemas.settings import SystemConfigResponse, SystemConfigUpdate

router = APIRouter()


def _get_defaults() -> SystemConfigResponse:
    return SystemConfigResponse(
        inference_confidence=app_settings.inference_confidence,
        max_queue_size=app_settings.max_queue_size,
        data_retention_days=app_settings.data_retention_days,
        alert_webhook_url=app_settings.alert_webhook_url,
        alert_webhook_enabled=app_settings.alert_webhook_enabled,
    )


@router.get("/settings", response_model=ApiResponse[SystemConfigResponse])
async def get_settings(
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(get_current_admin),
) -> ApiResponse[SystemConfigResponse]:
    defaults = _get_defaults().model_dump()
    for key in list(defaults.keys()):
        row = await session.get(SystemConfig, key)
        if row is not None:
            defaults[key] = json.loads(row.value)

    data = SystemConfigResponse(**defaults)
    return ApiResponse(code=0, message="success", data=data)


@router.put("/settings", response_model=ApiResponse[SystemConfigResponse])
async def update_settings(
    payload: SystemConfigUpdate,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(get_current_admin),
) -> ApiResponse[SystemConfigResponse]:
    current = _get_defaults().model_dump()
    current.update({k: v for k, v in payload.model_dump().items() if v is not None})

    for key, value in current.items():
        row = await session.get(SystemConfig, key)
        if row is None:
            row = SystemConfig(key=key, value=json.dumps(value), updated_at=datetime.utcnow())
            session.add(row)
        else:
            row.value = json.dumps(value)
            row.updated_at = datetime.utcnow()

    await session.commit()
    data = SystemConfigResponse(**current)
    return ApiResponse(code=0, message="success", data=data)
