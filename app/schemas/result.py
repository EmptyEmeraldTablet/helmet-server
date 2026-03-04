from datetime import datetime

from pydantic import BaseModel

from app.schemas.upload import Detection


class ResultItem(BaseModel):
    task_id: str
    device_id: str
    created_at: datetime
    annotated_image_url: str | None
    detections: list[Detection]
    has_violation: bool


class ResultListResponse(BaseModel):
    total: int
    items: list[ResultItem]


class ResultDetail(ResultItem):
    original_image_url: str | None
    process_time_ms: int | None
