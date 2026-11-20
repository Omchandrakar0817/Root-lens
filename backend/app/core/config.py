from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_name: str = "Incident RCA"
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/incident_rca"

    jwt_secret: str = "dev-only-access-secret-change-me-32"
    jwt_refresh_secret: str = "dev-only-refresh-secret-change-me-32"
    access_token_minutes: int = 20
    refresh_token_days: int = 7

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    pagespeed_api_key: str = ""

    max_websites_per_user: int = 10
    min_monitor_interval_seconds: int = 300
    scan_timeout_seconds: int = 15
    max_response_bytes: int = 1_000_000
    max_scans_per_hour: int = 12
    anomaly_min_samples: int = 30
    max_redirects: int = 3
    scan_lease_seconds: int = 120
    worker_concurrency_hint: int = 2

    admin_email: str = ""
    admin_password: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
