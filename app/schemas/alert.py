from datetime import datetime

from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: str
    task_id: str
    device_id: str
    violation_count: int
    is_read: bool
    created_at: datetime


class AlertListResponse(BaseModel):
    total: int
    items: list[AlertResponse]
