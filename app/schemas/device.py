from datetime import datetime

from pydantic import BaseModel


class DeviceCreateRequest(BaseModel):
    name: str | None = None


class DeviceUpdateRequest(BaseModel):
    name: str | None = None
    status: str | None = None


class DeviceResponse(BaseModel):
    id: str
    name: str | None
    status: str
    last_seen_at: datetime | None
    created_at: datetime


class DeviceCreateResponse(DeviceResponse):
    api_key: str
