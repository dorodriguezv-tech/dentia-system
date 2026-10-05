import uuid
from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import AuditedMixin, Base, UUIDPkMixin


class Provider(AuditedMixin, Base):
    """Identidad agendable de un profesional (CLAUDE.md Fase 6). Distinta de User
    porque trae datos propios de la agenda (color del calendario, activo o no) sin
    mezclarlos con el modulo iam."""

    __tablename__ = "providers"
    __table_args__ = (UniqueConstraint("clinic_id", "user_id", name="uq_provider_clinic_user"),)

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    color: Mapped[str] = mapped_column(String(7), default="#2BB3A3")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Resource(AuditedMixin, Base):
    """Gabinete o sillon reservable."""

    __tablename__ = "resources"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ProviderWorkingHours(UUIDPkMixin, Base):
    """Horario laboral recurrente de un profesional. Informativo para el calendario
    (zonas fuera de horario se muestran deshabilitadas); no bloquea agendar (regla
    configurable, ver docs/PENDIENTES_CLINICOS.md)."""

    __tablename__ = "provider_working_hours"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("providers.id", ondelete="CASCADE")
    )
    weekday: Mapped[int] = mapped_column(SmallInteger)  # 0=lunes .. 6=domingo
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)


class ProviderBlock(AuditedMixin, Base):
    """Bloqueo puntual (vacaciones, permiso, etc.) de un profesional."""

    __tablename__ = "provider_blocks"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("providers.id", ondelete="CASCADE")
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class Appointment(AuditedMixin, Base):
    """Cita (CLAUDE.md Fase 6, maquina de estados de docs/02 sec. 4).

    La proteccion contra traslapes vive en dos capas: el servicio valida antes de
    insertar (app/modules/agenda/service.py) y, como respaldo ante condiciones de
    carrera, dos restricciones EXCLUDE de Postgres (btree_gist + tstzrange) agregadas
    por SQL crudo en la migracion -- no son expresables en el ORM de SQLAlchemy, por
    eso no aparecen aqui (mismo patron que el indice trigram de patients, Fase 3).
    """

    __tablename__ = "appointments"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("providers.id", ondelete="RESTRICT")
    )
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("resources.id", ondelete="SET NULL"), nullable=True
    )
    appointment_type: Mapped[str] = mapped_column(String(30))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(15), default="RESERVADA")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rescheduled_from_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True
    )


class AppointmentStatusHistory(UUIDPkMixin, Base):
    __tablename__ = "appointment_status_history"

    appointment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE")
    )
    from_status: Mapped[str | None] = mapped_column(String(15), nullable=True)
    to_status: Mapped[str] = mapped_column(String(15))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WaitlistEntry(AuditedMixin, Base):
    __tablename__ = "waitlist_entries"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    provider_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("providers.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReminderTask(UUIDPkMixin, Base):
    """Tarea de recordatorio idempotente (CLAUDE.md Fase 6): solo se registra, el
    envio real no esta implementado todavia. uq_reminder_task_appointment_kind evita
    duplicados si la creacion de la cita se reintentara."""

    __tablename__ = "reminder_tasks"
    __table_args__ = (
        UniqueConstraint("appointment_id", "kind", name="uq_reminder_task_appointment_kind"),
    )

    appointment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("appointments.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(30))
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(10), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
