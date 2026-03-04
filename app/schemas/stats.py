from pydantic import BaseModel


class SummaryStats(BaseModel):
    total_today: int
    violations_today: int
    violation_rate: float
    active_devices: int


class TrendPoint(BaseModel):
    bucket: str
    count: int


class TrendResponse(BaseModel):
    granularity: str
    points: list[TrendPoint]


class DeviceStats(BaseModel):
    device_id: str
    count: int


class DeviceStatsResponse(BaseModel):
    items: list[DeviceStats]
