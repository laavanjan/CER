"""Application-wide configuration loaded from environment variables."""

from pydantic import field_validator
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

    # Anthropic (used by S9, primary LLM)
    anthropic_api_key: str = ""

    # Google Gemini (used by S9 as fallback when Anthropic fails)
    gemini_api_key: str = ""

    # Registry
    registry_path: str = "/registry/controls_v2.json"
    registry_version: str = "v2"

    # CORS — accepts a comma-separated string or a JSON array
    cors_origins: list[str] = ["http://localhost:3000"]

    # API key authentication — if unset, all requests are allowed
    api_key: str | None = None

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> object:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json
                return json.loads(v)
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
