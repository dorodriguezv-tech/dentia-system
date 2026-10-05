from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "DentalCare API"
    environment: str = "development"
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://dentia:dentia@localhost:5432/dentia"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_hours: int = 8

    cors_origins: list[str] = ["http://localhost:5173"]

    storage_dir: str = "../storage"

    ai_enabled: bool = True
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout_s: int = 60
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    ai_store_audio: bool = False
    ai_suggestion_ttl_hours: int = 24


@lru_cache
def get_settings() -> Settings:
    return Settings()
