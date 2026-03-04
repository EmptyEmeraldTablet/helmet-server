import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Alert, Detection, Task


async def cleanup_once(session: AsyncSession) -> None:
    cutoff = datetime.utcnow() - timedelta(days=settings.data_retention_days)

    result = await session.execute(
        select(Task).where(Task.created_at < cutoff)
    )
    tasks = result.scalars().all()

    for task in tasks:
        if task.original_image_path:
            Path(task.original_image_path).unlink(missing_ok=True)
        if task.annotated_image_path:
            Path(task.annotated_image_path).unlink(missing_ok=True)

    task_ids = [task.id for task in tasks]
    if task_ids:
        await session.execute(delete(Alert).where(Alert.task_id.in_(task_ids)))
        await session.execute(delete(Detection).where(Detection.task_id.in_(task_ids)))
        await session.execute(delete(Task).where(Task.id.in_(task_ids)))
        await session.commit()


async def cleanup_loop(session_factory) -> None:
    while True:
        async with session_factory() as session:
            await cleanup_once(session)
        await asyncio.sleep(24 * 60 * 60)
