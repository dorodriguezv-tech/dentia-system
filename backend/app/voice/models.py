import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, UUIDPkMixin


class VoiceCommandLog(UUIDPkMixin, Base):
    """Fase 13 ("Dentia"): registro de texto de las ORDENES dirigidas a Dentia --
    nunca el audio (docs/05_ASISTENTE_DENTIA_VOZ_CONVERSACIONAL.md sec. 9: se
    procesa en memoria y se descarta) y nunca la conversacion con el paciente,
    solo lo que se transcribe despues de detectar "Dentia". Append-only como
    AuditEvent, pero es un registro propio (no el mismo AuditEvent): este es
    telemetria de voz para medir aciertos/latencia (Fase 13.6), mientras que
    AuditEvent sigue siendo el registro de auditoria de la accion clinica en si
    (p.ej. ai.suggestion_accepted con confirmation_mode) una vez que exista.
    """

    __tablename__ = "voice_command_logs"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    # "wake_detected" es el unico evento de la etapa 13.1 (sin intenciones todavia);
    # 13.2+ agregara "intent"/"ask"/"confirm"/etc. sin tocar las columnas.
    event: Mapped[str] = mapped_column(String(30))
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmation_mode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    result: Mapped[str | None] = mapped_column(String(200), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
