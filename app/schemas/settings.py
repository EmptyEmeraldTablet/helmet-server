from pydantic import BaseModel


class SystemConfigResponse(BaseModel):
    inference_confidence: float
    max_queue_size: int
    data_retention_days: int
    alert_webhook_url: str
    alert_webhook_enabled: bool


class SystemConfigUpdate(BaseModel):
    inference_confidence: float | None = None
    max_queue_size: int | None = None
    data_retention_days: int | None = None
    alert_webhook_url: str | None = None
    alert_webhook_enabled: bool | None = None
