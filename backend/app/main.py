from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.audit.middleware import AccessDeniedAuditMiddleware
from app.core.config import get_settings
from app.core.db import async_session_factory
from app.core.errors import register_error_handlers
from app.modules.branding.router import router as branding_router
from app.modules.encounters.router import router as encounters_router
from app.modules.iam.router import router as iam_router
from app.modules.odontogram.router import router as odontogram_router
from app.modules.patients.router import router as patients_router
from app.modules.records.router import router as records_router

settings = get_settings()

app = FastAPI(title=settings.app_name)
app.state.db_sessionmaker = async_session_factory

app.add_middleware(AccessDeniedAuditMiddleware)
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


@app.get(f"{settings.api_prefix}/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
