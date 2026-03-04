import json
from datetime import datetime

from sqlalchemy import select

from app.config import settings
from app.db.database import Base, SessionLocal, engine
from app.models import AdminUser, SystemConfig
from app.utils.security import hash_secret


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as session:
        existing = await session.execute(
            select(AdminUser).where(AdminUser.username == settings.admin_username)
        )
        if existing.scalar_one_or_none() is None:
            session.add(
                AdminUser(
                    username=settings.admin_username,
                    password_hash=hash_secret(settings.admin_password),
                )
            )

        defaults = {
            "inference_confidence": settings.inference_confidence,
            "max_queue_size": settings.max_queue_size,
            "data_retention_days": settings.data_retention_days,
            "alert_webhook_url": settings.alert_webhook_url,
            "alert_webhook_enabled": settings.alert_webhook_enabled,
        }
        for key, value in defaults.items():
            row = await session.get(SystemConfig, key)
            if row is None:
                session.add(
                    SystemConfig(
                        key=key,
                        value=json.dumps(value),
                        updated_at=datetime.utcnow(),
                    )
                )

        await session.commit()
