import uuid
from collections.abc import AsyncGenerator
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    # SQLAlchemy async: una columna con onupdate=func.now() (updated_at, en AuditedMixin)
    # queda "expirada" tras un UPDATE porque el valor lo calcula el servidor. Sin
    # eager_defaults, leerla despues (p.ej. Pydantic model_validate) dispara una carga
    # perezosa que falla con MissingGreenlet fuera de un await. eager_defaults pide ese
    # valor con RETURNING en el mismo INSERT/UPDATE, sin round-trip extra.
    __mapper_args__ = {"eager_defaults": True}


class UUIDPkMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class AuditedMixin(UUIDPkMixin):
    """Columnas obligatorias de CLAUDE.md sec. 6: created_at, created_by, updated_at."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
