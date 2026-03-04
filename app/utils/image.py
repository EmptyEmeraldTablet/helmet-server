from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import settings


def ensure_storage_dirs() -> None:
    Path(settings.original_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.annotated_dir).mkdir(parents=True, exist_ok=True)


def generate_image_name(suffix: str = ".jpg") -> str:
    return f"{uuid4()}{suffix}"


async def save_upload_file(upload: UploadFile) -> str:
    ensure_storage_dirs()
    suffix = Path(upload.filename or "").suffix or ".jpg"
    filename = generate_image_name(suffix)
    destination = Path(settings.original_dir) / filename
    content = await upload.read()
    destination.write_bytes(content)
    return str(destination)
