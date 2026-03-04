from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import settings


def ensure_storage_dirs() -> None:
    Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
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


def build_storage_url(path: str | None) -> str | None:
    if not path:
        return None

    if path.startswith("/storage/"):
        return path

    if path.startswith("storage/"):
        return f"/{path.lstrip('/')}"

    storage_root = Path(settings.storage_dir)
    try:
        relative = Path(path).resolve().relative_to(storage_root.resolve())
        return f"/{storage_root.as_posix().strip('/')}/{relative.as_posix()}"
    except ValueError:
        path_posix = Path(path).as_posix()
        storage_name = storage_root.as_posix().rstrip("/")
        marker = f"{storage_name}/"
        index = path_posix.rfind(marker)
        if index != -1:
            tail = path_posix[index + len(marker) :]
            return f"/{storage_name}/{tail}"

    return f"/{storage_root.as_posix().strip('/')}/{Path(path).name}"
