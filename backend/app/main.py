from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.audit.middleware import AccessDeniedAuditMiddleware
from app.core.config import get_settings
from app.core.db import async_session_factory
from app.core.errors import register_error_handlers
from app.modules.iam.router import router as iam_router

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


@app.get(f"{settings.api_prefix}/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
