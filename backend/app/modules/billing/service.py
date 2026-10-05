import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import AppError
from app.modules.billing.models import Charge
from app.modules.patients.models import Patient


async def create_charge(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    procedure_performed_id: uuid.UUID,
    amount: Decimal,
    description: str | None,
    actor_id: uuid.UUID,
) -> Charge:
    """Genera el cargo sugerido (regla 4 de CLAUDE.md): nunca un pago, solo una
    sugerencia de cobro ligada al procedimiento realizado. Llamado desde
    treatment.service al registrar un ProcedurePerformed."""
    charge = Charge(
        clinic_id=clinic_id,
        patient_id=patient_id,
        procedure_performed_id=procedure_performed_id,
        amount=amount,
        status="SUGERIDO",
        description=description,
        created_by=actor_id,
    )
    db.add(charge)
    await db.flush()
    await audit_service.log(
        db,
        action="billing.charge_suggested",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="charge",
        entity_id=str(charge.id),
        details={"amount": str(amount), "procedure_performed_id": str(procedure_performed_id)},
    )
    return charge


async def list_charges(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[Charge]:
    patient = await db.get(Patient, patient_id)
    if patient is None or patient.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Paciente no encontrado", status_code=404)
    stmt = (
        select(Charge)
        .where(Charge.clinic_id == clinic_id, Charge.patient_id == patient_id)
        .order_by(Charge.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())
