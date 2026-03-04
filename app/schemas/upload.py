from pydantic import BaseModel, Field


class Detection(BaseModel):
    label: str
    confidence: float
    bbox: list[float] = Field(min_length=4, max_length=4)


class UploadResponseData(BaseModel):
    task_id: str
    status: str
    annotated_image_url: str | None
    detections: list[Detection]
    has_violation: bool
    process_time_ms: int | None
