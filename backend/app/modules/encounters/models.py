import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import AuditedMixin, Base


class Encounter(AuditedMixin, Base):
    __tablename__ = "encounters"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    professional_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True
    )
    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ClinicalNote(AuditedMixin, Base):
    __tablename__ = "clinical_notes"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )

    status: Mapped[str] = mapped_column(String(10), default="DRAFT")
    soap_s: Mapped[str | None] = mapped_column(Text, nullable=True)
    soap_o: Mapped[str | None] = mapped_column(Text, nullable=True)
    soap_a: Mapped[str | None] = mapped_column(Text, nullable=True)
    soap_p: Mapped[str | None] = mapped_column(Text, nullable=True)
    free_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    version: Mapped[int] = mapped_column(default=1)
    previous_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinical_notes.id", ondelete="SET NULL"), nullable=True
    )
    correction_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Fase D (docs/clinica/nota_evolucion.pdf): campos complementarios al SOAP
    # de arriba, nullable (no reemplazan soap_s/o/a/p/free_text ni el flujo de
    # estados DRAFT/FINAL/CORRECTED/CANCELLED). Si la nota ya es FINAL, se
    # editan por el mismo flujo de correccion (regla 1 de CLAUDE.md) --
    # ver encounters/service.py::update_note/correct_note.
    interrogatorio: Mapped[str | None] = mapped_column(Text, nullable=True)
    medicamentos: Mapped[str | None] = mapped_column(Text, nullable=True)
    estudios_radiograficos: Mapped[str | None] = mapped_column(Text, nullable=True)
    descripcion_procedimiento: Mapped[str | None] = mapped_column(Text, nullable=True)
    pronostico_evolucion: Mapped[str | None] = mapped_column(Text, nullable=True)
    indicaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_proxima_cita: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Texto libre (el formato original no exige una fecha estricta en este campo).
    fecha_proxima_cita: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evaluacion_actualizacion: Mapped[str | None] = mapped_column(Text, nullable=True)
