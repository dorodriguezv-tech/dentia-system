import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
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


class ProcedureCatalog(AuditedMixin, Base):
    """Catalogo de procedimientos con lista de precios por sucursal (CLAUDE.md Fase 7).
    A diferencia de los catalogos Python de fases anteriores, este vive en la BD
    porque el precio varia por clinica y debe poder editarse sin desplegar codigo."""

    __tablename__ = "procedure_catalog"
    __table_args__ = (
        UniqueConstraint("clinic_id", "code", name="uq_procedure_catalog_clinic_code"),
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(200))
    default_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TreatmentPlan(AuditedMixin, Base):
    """Plan de tratamiento y presupuesto (docs/02 sec. 4: BORRADOR -> PRESENTADO ->
    ACEPTADO (total o parcial) | RECHAZADO -> EN_PROGRESO -> TERMINADO)."""

    __tablename__ = "treatment_plans"

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
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(15), default="BORRADOR")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Quien acepta en la practica es el paciente o su tutor, no un usuario del sistema
    # (no hay portal/firma electronica todavia): se guarda el nombre tal cual lo dicta.
    accepted_by_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    acceptance_type: Mapped[str | None] = mapped_column(String(10), nullable=True)
    rejected_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class TreatmentPhase(AuditedMixin, Base):
    __tablename__ = "treatment_phases"

    plan_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("treatment_plans.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[str] = mapped_column(String(10), default="media")


class ProcedurePlanned(_AnnullableMixin, AuditedMixin, Base):
    """Lo planificado (regla 3 de CLAUDE.md): entidad separada de ProcedurePerformed,
    nunca se convierte en "realizado" in place. `alternative` agrupa procedimientos de
    una misma fase que son opciones mutuamente excluyentes (p.ej. "A" = corona,
    "B" = puente) -- ver docs/02_ARQUITECTURA.md sec. 5.7."""

    __tablename__ = "procedures_planned"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("treatment_plans.id", ondelete="CASCADE")
    )
    phase_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("treatment_phases.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )
    tooth_fdi: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    surface: Mapped[str | None] = mapped_column(String(1), nullable=True)
    procedure_code: Mapped[str] = mapped_column(String(50))
    procedure_name: Mapped[str] = mapped_column(String(200))
    # Hallazgo a reflejar en el odontograma como PLANNED (null si el procedimiento no
    # aplica a una pieza concreta, p.ej. una limpieza general).
    finding_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    alternative: Mapped[str] = mapped_column(String(10), default="A")
    discount_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    discount_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    discount_authorized_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)


class ProcedurePerformed(AuditedMixin, Base):
    """Lo realizado (regla 3): entidad separada de ProcedurePlanned. Si viene de un
    planificado, `planned_id` los enlaza, pero el planificado nunca se edita ni se
    borra -- queda igual en el historial del presupuesto."""

    __tablename__ = "procedures_performed"

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
    planned_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("procedures_planned.id", ondelete="SET NULL"),
        nullable=True,
    )
    tooth_fdi: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    surface: Mapped[str | None] = mapped_column(String(1), nullable=True)
    procedure_code: Mapped[str] = mapped_column(String(50))
    procedure_name: Mapped[str] = mapped_column(String(200))
    finding_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    material: Mapped[str | None] = mapped_column(String(100), nullable=True)
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
