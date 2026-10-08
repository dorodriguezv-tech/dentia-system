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

    # Fase 13 (Dentia, 13.1 "Base de voz"): ver docs/05_ASISTENTE_DENTIA_VOZ_CONVERSACIONAL.md
    # sec. 8. voice_wake_engine solo tiene "whisper_tiny" implementado (etapa 1) --
    # "openwakeword" (etapa 2, modelo propio entrenado) queda para 13.6.
    voice_enabled: bool = True
    voice_wake_engine: str = "whisper_tiny"
    voice_wake_model_size: str = "tiny"
    voice_tts_engine: str = "piper"
    voice_tts_model: str = "es_MX-claude-high"
    # Ruta al .onnx descargado con `python -m piper.download_voices` (ver
    # requirements.txt) -- si el archivo no existe (p.ej. no se ha corrido esa
    # descarga todavia), tts.py cae a None y el cliente usa speechSynthesis.
    voice_tts_model_path: str = "../voices/es_MX-claude-high.onnx"
    # Mismo patron que ai_fake_mode: respuestas deterministas sin audio/modelos reales,
    # para pruebas automatizadas y E2E. Nunca se activa en produccion.
    voice_fake_mode: bool = False

    # Fase 13 (Dentia, 13.3 "Captura en consulta"): niveles de confirmacion y
    # ventana de seguimiento, sec. 2.1, 3 y 8 del diseno. Las pruebas bajan
    # voice_capture_countdown_s para no esperar tiempo real.
    voice_capture_countdown_s: float = 3.0
    voice_followup_s: float = 8.0

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
