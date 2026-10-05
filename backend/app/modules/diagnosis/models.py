import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import AuditedMixin, Base


class _AnnullableMixin:
    """Regla 2 de CLAUDE.md: sin borrado fisico, se anula con motivo y queda auditado."""

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    annul_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    annulled_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    annulled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Diagnosis(_AnnullableMixin, AuditedMixin, Base):
    """Diagnostico clinico (regla 6: fecha, autor y contexto de encounter obligatorios)."""

    __tablename__ = "diagnoses"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )
    professional_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    tooth_fdi: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    surface: Mapped[str | None] = mapped_column(String(1), nullable=True)
    code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    text: Mapped[str] = mapped_column(Text)
