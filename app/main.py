import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import upload
from app.config import settings
from app.core.queue_worker import TaskQueue, worker_loop
from app.db.database import SessionLocal
from app.db.init_db import init_db
from app.utils.image import ensure_storage_dirs


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_storage_dirs()
    await init_db()
    app.state.session_factory = SessionLocal
    queue = TaskQueue(settings.max_queue_size)
    upload.set_queue(queue)
    worker_task = asyncio.create_task(worker_loop(queue, app.state.session_factory))
    yield
    worker_task.cancel()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix=settings.api_prefix, tags=["upload"])


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}
