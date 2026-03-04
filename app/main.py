import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import alerts, auth, devices, settings, stats, upload, websocket
from app.config import settings
from app.core.broadcast import ConnectionManager
from app.core.cleanup import cleanup_loop
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

    manager = ConnectionManager()
    websocket.set_manager(manager)

    worker_task = asyncio.create_task(worker_loop(queue, app.state.session_factory, manager))
    cleanup_task = asyncio.create_task(cleanup_loop(app.state.session_factory))
    yield
    worker_task.cancel()
    cleanup_task.cancel()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix=settings.api_prefix, tags=["upload"])
app.include_router(auth.router, prefix=settings.api_prefix, tags=["auth"])
app.include_router(devices.router, prefix=settings.api_prefix, tags=["devices"])
app.include_router(alerts.router, prefix=settings.api_prefix, tags=["alerts"])
app.include_router(stats.router, prefix=settings.api_prefix, tags=["stats"])
app.include_router(settings.router, prefix=settings.api_prefix, tags=["settings"])
app.include_router(websocket.router, tags=["websocket"])


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}
