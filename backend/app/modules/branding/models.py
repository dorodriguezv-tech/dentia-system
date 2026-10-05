import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.modules.branding.presets import DEFAULT_PRESET


class ClinicBranding(Base):
    """Una fila por sucursal (docs/04_TEMAS_Y_MARCA.md sec. 6). clinic_id es la PK."""

    __tablename__ = "clinic_branding"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), primary_key=True
    )
    display_name: Mapped[str] = mapped_column(String(200))
    subtitle: Mapped[str | None] = mapped_column(String(300), nullable=True)
    logo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    favicon_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preset: Mapped[str] = mapped_column(String(50), default=DEFAULT_PRESET)
    colors: Mapped[dict[str, Any]] = mapped_column(JSONB)
    dark_mode: Mapped[bool] = mapped_column(Boolean, default=False)
    radius: Mapped[str] = mapped_column(String(10), default="soft")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
