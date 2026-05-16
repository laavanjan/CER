"""Application-wide configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://ethiksa:ethiksa@postgres:5432/ethiksa"

    # Redis / Celery broker (primary)
    redis_url: str = "redis://redis:6379/0"

    # Redis fallback — used automatically if primary is unreachable or over limit
    redis_fallback_url: str = ""

    # S3 / MinIO
    s3_endpoint_url: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "ethiksa-cer"

    # GitHub token for cloning private repos (optional — public repos work without it)
    github_token: str = ""

    # Anthropic (used by S9, primary LLM)
    anthropic_api_key: str = ""

    # Ollama Cloud (used by S9 as first fallback)
    ollama_api_key: str = ""

    # Google Gemini (used by S9 as last resort fallback)
    gemini_api_key: str = ""

    # Registry
    registry_path: str = "/registry/controls_v2.json"
    registry_version: str = "v2"

    # CORS — comma-separated string (e.g. "http://localhost:3000,https://app.vercel.app")
    cors_origins: str = "http://localhost:3000"

    # API key authentication — if unset, all requests are allowed
    api_key: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        v = self.cors_origins.strip()
        if v.startswith("["):
            import json
            return json.loads(v)
        return [o.strip() for o in v.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
