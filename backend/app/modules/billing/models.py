import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import AuditedMixin, Base


class _CancellableMixin:
    """Regla 2 de CLAUDE.md: sin borrado fisico, se cancela con motivo y queda
    auditado. `cancel_authorized_by` existe porque cancelar un cargo o un pago es
    sensible (dinero), igual que `discount_authorized_by` en treatment (Fase 7); para
    el MVP es siempre quien hace la peticion (ya validado por `billing.write`), no un
    segundo aprobador -- ver docs/PENDIENTES_CLINICOS.md."""

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    cancel_authorized_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Charge(_CancellableMixin, AuditedMixin, Base):
    """Cargo sugerido al registrar un procedimiento realizado (CLAUDE.md Fase 7 y
    regla 4: un presupuesto aceptado no es un pago, y un pago no cambia el estado
    clinico). `status` es un valor historico ("SUGERIDO", puesto por treatment.service
    al crearlo) que ya no se usa para mostrar el estado de cobro -- ver
    rules.charge_computed_status, que lo calcula a partir de PaymentAllocation."""

    __tablename__ = "charges"
    __table_args__ = (
        UniqueConstraint("procedure_performed_id", name="uq_charge_procedure_performed"),
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    procedure_performed_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("procedures_performed.id", ondelete="CASCADE")
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(15), default="SUGERIDO")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class CashSession(AuditedMixin, Base):
    """Corte de caja por sesion (CLAUDE.md Fase 10): abre con un monto inicial de
    efectivo, cierra con el monto contado; la diferencia contra lo esperado (apertura +
    cobros en efectivo de la sesion) se calcula en el servicio, no se guarda aqui."""

    __tablename__ = "cash_sessions"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    opened_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    opening_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(10), default="ABIERTA")
    closed_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closing_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Payment(_CancellableMixin, AuditedMixin, Base):
    """Pago (CLAUDE.md Fase 10, regla 4: nunca cambia el estado clinico). Puede llegar
    sin ninguna aplicacion a un cargo (anticipo: credito del paciente para usar
    despues) -- ver PaymentAllocation."""

    __tablename__ = "payments"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    cash_session_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("cash_sessions.id", ondelete="SET NULL"), nullable=True
    )
    method: Mapped[str] = mapped_column(String(15))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Folio/autorizacion de la terminal o de la transferencia; libre porque cada banco o
    # procesador de pagos tiene su propio formato.
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PaymentAllocation(AuditedMixin, Base):
    """Aplica (total o parcialmente) un Payment a un Charge. La suma de aplicaciones de
    un pago no puede superar su monto, ni la suma de aplicaciones de un cargo puede
    superar el suyo (validado en el servicio, no aqui). Si el Payment se cancela, sus
    aplicaciones no se borran (regla 2): se excluyen del saldo calculado porque
    Payment.is_active pasa a False -- el historial completo queda intacto."""

    __tablename__ = "payment_allocations"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("payments.id", ondelete="CASCADE")
    )
    charge_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("charges.id", ondelete="CASCADE")
    )
    amount_applied: Mapped[Decimal] = mapped_column(Numeric(10, 2))


class ClinicBillingSettings(Base):
    """Una fila por sucursal (mismo patron que ClinicBranding y AiClinicSettings): la
    cobranza puede desactivarse por sucursal para instalaciones donde no se cobra de
    verdad (p.ej. clinicas universitarias de practica) -- ver
    docs/PENDIENTES_CLINICOS.md."""

    __tablename__ = "clinic_billing_settings"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), primary_key=True
    )
    billing_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
