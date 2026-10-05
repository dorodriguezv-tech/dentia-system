import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import AuditedMixin, Base


class AiSuggestion(AuditedMixin, Base):
    """Una propuesta de la IA (regla 9 de CLAUDE.md): PENDING hasta que el odontologo la
    acepta o rechaza. Cada accion de un mismo dictado (POST /ai/interpret) crea una fila
    propia -- no una sola fila con la lista completa -- para poder aceptar/editar/rechazar
    cada una por separado, tal como pide el panel "Propuestas del asistente". `batch_id`
    agrupa las filas que vinieron del mismo dictado, solo para mostrarlas juntas en la UI."""

    __tablename__ = "ai_suggestions"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )
    batch_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True))
    action_type: Mapped[str] = mapped_column(String(40))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(10), default="PENDING")

    # Trazabilidad de origen (docs/03 sec. 9): modelo, digest y extracto del dictado
    # que produjo esta sugerencia, para poder auditar de donde vino cada propuesta.
    model_name: Mapped[str] = mapped_column(String(100))
    model_digest: Mapped[str | None] = mapped_column(String(100), nullable=True)
    transcript_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class AiClinicSettings(Base):
    """Preferencias de IA por sucursal (una fila por clinica, igual que ClinicBranding
    en la Fase 2): hoy solo el modelo de Ollama a usar. AI_STORE_AUDIO es deliberadamente
    global (.env), no editable por sucursal -- ver docs/PENDIENTES_CLINICOS.md."""

    __tablename__ = "ai_clinic_settings"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), primary_key=True
    )
    ollama_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
