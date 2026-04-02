from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Helmet Detection Server"
    api_prefix: str = "/api"

    storage_dir: str = "storage"
    original_dir: str = "storage/original"
    annotated_dir: str = "storage/annotated"
    weights_path: str = "weights/best.pt"

    database_url: str = "sqlite+aiosqlite:///./helmet.db"
    inference_confidence: float = 0.5
    max_queue_size: int = 10

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    admin_username: str = "admin"
    admin_password: str = "admin123"
    password_hash_scheme: str = "bcrypt"

    alert_webhook_url: str = ""
    alert_webhook_enabled: bool = False
    data_retention_days: int = 30
    preserve_stream_data: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
