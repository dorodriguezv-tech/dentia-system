from functools import lru_cache
from typing import Self

from pydantic import model_validator
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

    cors_origins: list[str] = ["http://localhost:5174"]

    storage_dir: str = "../storage"

    ai_enabled: bool = True
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout_s: int = 120
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    ai_store_audio: bool = False
    ai_suggestion_ttl_hours: int = 24
    # Fase 12 (E2E): respuestas deterministas sin red, para que Playwright corra el
    # flujo completo con IA sin depender de un Ollama/Whisper reales. Nunca se activa
    # en produccion -- ver backend/app/ai/ollama_client.py y e2e/playwright.config.ts.
    ai_fake_mode: bool = False

    @model_validator(mode="after")
    def _require_real_jwt_secret_in_production(self) -> Self:
        # Fase 12 (revision de seguridad, OWASP A02/A07): el valor por defecto es solo
        # para desarrollo -- arrancar en produccion sin JWT_SECRET propio firmaria
        # tokens con un secreto publico (este mismo repositorio).
        if self.environment == "production" and self.jwt_secret == "change-me":
            raise ValueError(
                "JWT_SECRET no puede quedarse en el valor por defecto ('change-me') "
                "cuando ENVIRONMENT=production. Define uno propio en backend/.env."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def docs_urls(environment: str) -> tuple[str | None, str | None, str | None]:
    """(docs_url, redoc_url, openapi_url) para FastAPI segun el entorno.

    Fase 12 (revision de seguridad): Swagger/Redoc cargan su bundle de un CDN y
    exponen el esquema completo de la API -- utiles en desarrollo, pero superficie
    innecesaria en produccion.
    """
    if environment == "production":
        return None, None, None
    return "/docs", "/redoc", "/openapi.json"
