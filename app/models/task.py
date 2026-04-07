from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    original_image_path: Mapped[str | None] = mapped_column(String(256), nullable=True)
    annotated_image_path: Mapped[str | None] = mapped_column(String(256), nullable=True)
    process_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_violation: Mapped[bool] = mapped_column(Boolean, default=False)
    model_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    label_set: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("stream_sessions.id"), nullable=True, index=True
    )
    frame_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("stream_frames.id"), nullable=True, index=True
    )

    detections: Mapped[list["Detection"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    alert: Mapped["Alert | None"] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        uselist=False,
    )
    device: Mapped["Device"] = relationship(back_populates="tasks")
    session: Mapped["StreamSession | None"] = relationship(back_populates="tasks")
    frame: Mapped["StreamFrame | None"] = relationship(back_populates="task")


class Detection(Base):
    __tablename__ = "detections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), ForeignKey("tasks.id"), index=True)
    label: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column()
    bbox_x1: Mapped[float] = mapped_column()
    bbox_y1: Mapped[float] = mapped_column()
    bbox_x2: Mapped[float] = mapped_column()
    bbox_y2: Mapped[float] = mapped_column()

    task: Mapped[Task] = relationship(back_populates="detections")
