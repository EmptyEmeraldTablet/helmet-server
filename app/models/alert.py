from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), index=True)
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id"), index=True)
    violation_count: Mapped[int] = mapped_column(Integer, default=0)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    task: Mapped["Task"] = relationship(back_populates="alert")
    device: Mapped["Device"] = relationship(back_populates="alerts")
