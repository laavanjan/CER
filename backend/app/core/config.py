"""Application-wide configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://ethiksa:ethiksa@postgres:5432/ethiksa"

    # Redis / Celery broker
    redis_url: str = "redis://redis:6379/0"

    # S3 / MinIO
    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "ethiksa-cer"

    # Anthropic (used by S9)
    anthropic_api_key: str = ""

    # Registry
    registry_path: str = "/registry/controls_v2.json"
    registry_version: str = "v2"

    # CORS — comma-separated list
    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
