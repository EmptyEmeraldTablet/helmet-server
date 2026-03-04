import asyncio
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("PASSWORD_HASH_SCHEME", "pbkdf2_sha256")

from app.main import app
from app.db.database import SessionLocal
from app.models import AdminUser
from app.utils.security import hash_secret


class _StubEngine:
    def predict(self, image_path: str):
        detections = [
            {
                "label": "person",
                "confidence": 0.95,
                "bbox": [10.0, 10.0, 120.0, 180.0],
            },
            {
                "label": "no_helmet",
                "confidence": 0.88,
                "bbox": [40.0, 20.0, 90.0, 80.0],
            },
        ]
        return detections, 12.3, None


@pytest.fixture()
def stub_inference(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core import queue_worker

    monkeypatch.setattr(queue_worker, "get_engine", lambda: _StubEngine())


async def _ensure_admin() -> None:
    async with SessionLocal() as session:
        result = await session.execute(select(AdminUser).where(AdminUser.username == 'admin'))
        admin = result.scalar_one_or_none()
        if admin is None:
            session.add(AdminUser(username='admin', password_hash=hash_secret('admin123')))
        else:
            admin.password_hash = hash_secret('admin123')
        await session.commit()


@pytest.fixture()
def client(stub_inference: None) -> TestClient:
    with TestClient(app) as client:
        asyncio.run(_ensure_admin())
        yield client
