from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.dependencies import get_current_admin
from app.models import Device
from app.schemas.common import ApiResponse
from app.schemas.device import (
    DeviceCreateRequest,
    DeviceCreateResponse,
    DeviceResponse,
    DeviceUpdateRequest,
)
from app.utils.security import generate_api_key, hash_secret

router = APIRouter()


@router.get("/devices", response_model=ApiResponse[list[DeviceResponse]])
async def list_devices(
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(get_current_admin),
) -> ApiResponse[list[DeviceResponse]]:
    result = await session.execute(select(Device))
    devices = result.scalars().all()
    data = [
        DeviceResponse(
            id=device.id,
            name=device.name,
            status=device.status,
            last_seen_at=device.last_seen_at,
            created_at=device.created_at,
        )
        for device in devices
    ]
    return ApiResponse(code=0, message="success", data=data)


@router.post("/devices", response_model=ApiResponse[DeviceCreateResponse])
async def create_device(
    payload: DeviceCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(get_current_admin),
) -> ApiResponse[DeviceCreateResponse]:
    api_key = generate_api_key()
    device = Device(
        id=str(uuid4()),
        name=payload.name,
        api_key_hash=hash_secret(api_key),
        status="active",
        created_at=datetime.utcnow(),
    )
    session.add(device)
    await session.commit()

    data = DeviceCreateResponse(
        id=device.id,
        name=device.name,
        status=device.status,
        last_seen_at=device.last_seen_at,
        created_at=device.created_at,
        api_key=api_key,
    )
    return ApiResponse(code=0, message="success", data=data)


@router.put("/devices/{device_id}", response_model=ApiResponse[DeviceResponse])
async def update_device(
    device_id: str,
    payload: DeviceUpdateRequest,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(get_current_admin),
) -> ApiResponse[DeviceResponse]:
    device = await session.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    if payload.name is not None:
        device.name = payload.name
    if payload.status is not None:
        device.status = payload.status

    await session.commit()

    data = DeviceResponse(
        id=device.id,
        name=device.name,
        status=device.status,
        last_seen_at=device.last_seen_at,
        created_at=device.created_at,
    )
    return ApiResponse(code=0, message="success", data=data)


@router.delete("/devices/{device_id}", response_model=ApiResponse[DeviceResponse])
async def disable_device(
    device_id: str,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(get_current_admin),
) -> ApiResponse[DeviceResponse]:
    device = await session.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    device.status = "disabled"
    await session.commit()

    data = DeviceResponse(
        id=device.id,
        name=device.name,
        status=device.status,
        last_seen_at=device.last_seen_at,
        created_at=device.created_at,
    )
    return ApiResponse(code=0, message="success", data=data)


@router.post("/devices/{device_id}/regenerate-key", response_model=ApiResponse[DeviceCreateResponse])
async def regenerate_key(
    device_id: str,
    session: AsyncSession = Depends(get_db_session),
    admin=Depends(get_current_admin),
) -> ApiResponse[DeviceCreateResponse]:
    device = await session.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    api_key = generate_api_key()
    device.api_key_hash = hash_secret(api_key)
    await session.commit()

    data = DeviceCreateResponse(
        id=device.id,
        name=device.name,
        status=device.status,
        last_seen_at=device.last_seen_at,
        created_at=device.created_at,
        api_key=api_key,
    )
    return ApiResponse(code=0, message="success", data=data)
