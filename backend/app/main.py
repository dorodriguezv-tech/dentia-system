from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.router import router as ai_router
from app.audit.middleware import AccessDeniedAuditMiddleware
from app.core.config import docs_urls, get_settings
from app.core.db import async_session_factory, get_db
from app.core.errors import AppError, register_error_handlers
from app.core.security_headers import SecurityHeadersMiddleware
from app.modules.agenda.router import router as agenda_router
from app.modules.billing.router import router as billing_router
from app.modules.branding.router import router as branding_router
from app.modules.catalogs.router import router as catalogs_router
from app.modules.diagnosis.router import router as diagnosis_router
from app.modules.documents.router import router as documents_router
from app.modules.encounters.router import router as encounters_router
from app.modules.iam.router import router as iam_router
from app.modules.imaging.router import router as imaging_router
from app.modules.odontogram.router import router as odontogram_router
from app.modules.patients.router import router as patients_router
from app.modules.records.router import router as records_router
from app.modules.reports.router import router as reports_router
from app.modules.treatment.router import router as treatment_router
from app.voice import tts as voice_tts
from app.voice.router import router as voice_router

settings = get_settings()
_docs_url, _redoc_url, _openapi_url = docs_urls(settings.environment)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    # Dentia (Fase 13): no dejar el subproceso de Piper huerfano al apagar el
    # backend (ver app/voice/tts.py).
    await voice_tts.shutdown()


app = FastAPI(
    title=settings.app_name,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
    lifespan=_lifespan,
)
app.state.db_sessionmaker = async_session_factory

app.add_middleware(AccessDeniedAuditMiddleware)
app.add_middleware(SecurityHeadersMiddleware, environment=settings.environment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(iam_router, prefix=settings.api_prefix)
app.include_router(branding_router, prefix=settings.api_prefix)
app.include_router(patients_router, prefix=settings.api_prefix)
app.include_router(records_router, prefix=settings.api_prefix)
app.include_router(encounters_router, prefix=settings.api_prefix)
app.include_router(odontogram_router, prefix=settings.api_prefix)
app.include_router(agenda_router, prefix=settings.api_prefix)
app.include_router(diagnosis_router, prefix=settings.api_prefix)
app.include_router(treatment_router, prefix=settings.api_prefix)
app.include_router(billing_router, prefix=settings.api_prefix)
app.include_router(ai_router, prefix=settings.api_prefix)
app.include_router(documents_router, prefix=settings.api_prefix)
app.include_router(imaging_router, prefix=settings.api_prefix)
app.include_router(reports_router, prefix=settings.api_prefix)
app.include_router(catalogs_router, prefix=settings.api_prefix)
app.include_router(voice_router, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    # Fase "Publicacion en Hostinger" sec. 6, cambio #8: lo usan tanto el
    # healthcheck de Docker (docker-compose.yml) como el monitor externo
    # (UptimeRobot/Better Stack) -- sin tocar la base, una API "viva" pero sin
    # conexion a PostgreSQL se reportaria como sana cuando no lo esta.
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise AppError(
            "DATABASE_UNAVAILABLE", "No se pudo conectar a la base de datos", status_code=503
        ) from exc
    return {"status": "ok"}
