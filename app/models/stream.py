from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class StreamSession(Base):
    __tablename__ = "stream_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(36), ForeignKey("devices.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    fps_target: Mapped[int] = mapped_column(Integer, default=1)
    resolution: Mapped[str] = mapped_column(String(32), default="")
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    device: Mapped["Device"] = relationship(back_populates="stream_sessions")
    frames: Mapped[list["StreamFrame"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class StreamFrame(Base):
    __tablename__ = "stream_frames"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("stream_sessions.id"), index=True
    )
    frame_index: Mapped[int] = mapped_column(Integer, index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    image_path: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="queued")

    session: Mapped[StreamSession] = relationship(back_populates="frames")
    task: Mapped["Task | None"] = relationship(
        back_populates="frame",
        uselist=False,
    )
