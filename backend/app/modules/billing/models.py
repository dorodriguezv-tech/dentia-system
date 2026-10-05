import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import AuditedMixin, Base


class Charge(AuditedMixin, Base):
    """Cargo sugerido al registrar un procedimiento realizado (CLAUDE.md Fase 6/7 y
    regla 4: un presupuesto aceptado no es un pago, y un pago no cambia el estado
    clinico). Este modulo es deliberadamente minimo: Charge existe para que la Fase 7
    pueda "generar un cargo sugerido" sin inventar pagos; Payment, estados de cobro y
    el resto de la cobranza llegan completos en la Fase 10."""

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
