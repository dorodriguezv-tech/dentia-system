import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import AppError
from app.core.storage import StorageBackend
from app.modules.billing import rules
from app.modules.billing.models import (
    CashSession,
    Charge,
    ClinicBillingSettings,
    Payment,
    PaymentAllocation,
)
from app.modules.billing.pdf import AllocationRow, build_receipt_pdf
from app.modules.billing.schemas import PaymentCreateRequest
from app.modules.branding import service as branding_service
from app.modules.iam.models import User
from app.modules.patients.models import Patient

PAYMENT_METHOD_LABELS = {
    "efectivo": "Efectivo",
    "tarjeta": "Tarjeta",
    "transferencia": "Transferencia",
}


async def _get_patient_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> Patient:
    patient = await db.get(Patient, patient_id)
    if patient is None or patient.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Paciente no encontrado", status_code=404)
    return patient


async def _require_billing_enabled(db: AsyncSession, *, clinic_id: uuid.UUID) -> None:
    settings = await db.get(ClinicBillingSettings, clinic_id)
    if settings is not None and not settings.billing_enabled:
        raise AppError(
            "BILLING_DISABLED",
            "La cobranza esta desactivada para esta sucursal",
            status_code=403,
        )


# --------------------------------------------------------------------------- cargos


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
    treatment.service al registrar un ProcedurePerformed -- se crea siempre, incluso si
    la cobranza esta desactivada para la sucursal (es un registro clinico de lo que
    costaria, no un cobro de verdad; ver docs/PENDIENTES_CLINICOS.md)."""
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


async def _applied_amounts_by_charge(
    db: AsyncSession, *, charge_ids: list[uuid.UUID]
) -> dict[uuid.UUID, Decimal]:
    if not charge_ids:
        return {}
    stmt = (
        select(PaymentAllocation.charge_id, PaymentAllocation.amount_applied)
        .join(Payment, Payment.id == PaymentAllocation.payment_id)
        .where(PaymentAllocation.charge_id.in_(charge_ids), Payment.is_active.is_(True))
    )
    totals: dict[uuid.UUID, Decimal] = dict.fromkeys(charge_ids, Decimal("0.00"))
    for charge_id, amount_applied in (await db.execute(stmt)).all():
        totals[charge_id] = totals.get(charge_id, Decimal("0.00")) + amount_applied
    return totals


async def list_charges(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[tuple[Charge, Decimal, Decimal]]:
    """Devuelve cada cargo junto con lo aplicado y el saldo (regla 4: calculado a
    partir de los pagos activos, no de una bandera guardada)."""
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(Charge)
        .where(Charge.clinic_id == clinic_id, Charge.patient_id == patient_id)
        .order_by(Charge.created_at.desc())
    )
    charges = list((await db.execute(stmt)).scalars().all())
    applied_by_charge = await _applied_amounts_by_charge(db, charge_ids=[c.id for c in charges])
    return [
        (
            charge,
            applied_by_charge[charge.id],
            rules.charge_balance(charge.amount, applied_by_charge[charge.id]),
        )
        for charge in charges
    ]


async def _get_charge_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, charge_id: uuid.UUID
) -> Charge:
    charge = await db.get(Charge, charge_id)
    if charge is None or charge.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Cargo no encontrado", status_code=404)
    return charge


async def cancel_charge(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    charge_id: uuid.UUID,
    reason: str,
    actor_id: uuid.UUID,
) -> Charge:
    charge = await _get_charge_in_clinic(db, clinic_id=clinic_id, charge_id=charge_id)
    applied = (await _applied_amounts_by_charge(db, charge_ids=[charge_id]))[charge_id]
    if applied > 0:
        raise AppError(
            "CHARGE_HAS_PAYMENTS",
            "Este cargo ya tiene pagos aplicados; cancela esos pagos primero",
            status_code=409,
        )

    charge.is_active = False
    charge.cancel_reason = reason
    charge.cancelled_by = actor_id
    charge.cancel_authorized_by = actor_id
    charge.cancelled_at = datetime.now(UTC)

    await audit_service.log(
        db,
        action="billing.charge_cancelled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="charge",
        entity_id=str(charge_id),
        details={"reason": reason},
    )
    await db.commit()
    return charge


# --------------------------------------------------------------------------- pagos


async def _get_open_cash_session(db: AsyncSession, *, clinic_id: uuid.UUID) -> CashSession | None:
    stmt = select(CashSession).where(
        CashSession.clinic_id == clinic_id, CashSession.status == "ABIERTA"
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def create_payment(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: PaymentCreateRequest,
    actor_id: uuid.UUID,
) -> tuple[Payment, list[PaymentAllocation]]:
    await _require_billing_enabled(db, clinic_id=clinic_id)
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)

    charge_ids = [a.charge_id for a in data.allocations]
    charges_by_id: dict[uuid.UUID, Charge] = {}
    if charge_ids:
        applied_by_charge = await _applied_amounts_by_charge(db, charge_ids=charge_ids)
        for allocation in data.allocations:
            charge = await _get_charge_in_clinic(
                db, clinic_id=clinic_id, charge_id=allocation.charge_id
            )
            if charge.patient_id != patient_id:
                raise AppError(
                    "CHARGE_PATIENT_MISMATCH",
                    "El cargo no pertenece a este paciente",
                    status_code=400,
                )
            if not charge.is_active:
                raise AppError("CHARGE_CANCELLED", "Este cargo esta cancelado", status_code=409)
            balance = rules.charge_balance(charge.amount, applied_by_charge[allocation.charge_id])
            if allocation.amount > balance:
                raise AppError(
                    "ALLOCATION_EXCEEDS_BALANCE",
                    f"El monto aplicado supera el saldo pendiente del cargo ({balance})",
                    status_code=422,
                )
            charges_by_id[allocation.charge_id] = charge

    session = await _get_open_cash_session(db, clinic_id=clinic_id)
    payment = Payment(
        clinic_id=clinic_id,
        patient_id=patient_id,
        cash_session_id=session.id if session else None,
        method=data.method,
        amount=data.amount,
        reference=data.reference,
        notes=data.notes,
        created_by=actor_id,
    )
    db.add(payment)
    await db.flush()

    created_allocations: list[PaymentAllocation] = []
    for allocation in data.allocations:
        allocation_row = PaymentAllocation(
            clinic_id=clinic_id,
            payment_id=payment.id,
            charge_id=allocation.charge_id,
            amount_applied=allocation.amount,
            created_by=actor_id,
        )
        db.add(allocation_row)
        created_allocations.append(allocation_row)
    await db.flush()

    await audit_service.log(
        db,
        action="billing.payment_received",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="payment",
        entity_id=str(payment.id),
        details={
            "patient_id": str(patient_id),
            "method": data.method,
            "amount": str(data.amount),
            "allocations": [str(a.charge_id) for a in data.allocations],
        },
    )
    await db.commit()
    return payment, created_allocations


async def _allocations_for_payment(
    db: AsyncSession, *, payment_id: uuid.UUID
) -> list[PaymentAllocation]:
    stmt = select(PaymentAllocation).where(PaymentAllocation.payment_id == payment_id)
    return list((await db.execute(stmt)).scalars().all())


async def list_payments(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[tuple[Payment, list[PaymentAllocation]]]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(Payment)
        .where(Payment.clinic_id == clinic_id, Payment.patient_id == patient_id)
        .order_by(Payment.received_at.desc())
    )
    payments = list((await db.execute(stmt)).scalars().all())
    return [
        (payment, await _allocations_for_payment(db, payment_id=payment.id)) for payment in payments
    ]


async def _get_payment_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, payment_id: uuid.UUID
) -> Payment:
    payment = await db.get(Payment, payment_id)
    if payment is None or payment.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Pago no encontrado", status_code=404)
    return payment


async def cancel_payment(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    payment_id: uuid.UUID,
    reason: str,
    actor_id: uuid.UUID,
) -> tuple[Payment, list[PaymentAllocation]]:
    payment = await _get_payment_in_clinic(db, clinic_id=clinic_id, payment_id=payment_id)
    payment.is_active = False
    payment.cancel_reason = reason
    payment.cancelled_by = actor_id
    payment.cancel_authorized_by = actor_id
    payment.cancelled_at = datetime.now(UTC)

    await audit_service.log(
        db,
        action="billing.payment_cancelled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="payment",
        entity_id=str(payment_id),
        details={"reason": reason},
    )
    await db.commit()
    return payment, await _allocations_for_payment(db, payment_id=payment.id)


async def build_receipt(
    db: AsyncSession, storage: StorageBackend, *, clinic_id: uuid.UUID, payment_id: uuid.UUID
) -> bytes:
    payment = await _get_payment_in_clinic(db, clinic_id=clinic_id, payment_id=payment_id)
    patient = await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=payment.patient_id)
    allocations = await _allocations_for_payment(db, payment_id=payment.id)

    branding = await branding_service.get_branding(db)
    logo = await branding_service.read_logo(db, storage)
    received_by = await db.get(User, payment.created_by) if payment.created_by else None

    allocation_rows = []
    allocated_total = Decimal("0.00")
    for allocation in allocations:
        charge = await db.get(Charge, allocation.charge_id)
        label = charge.description if charge and charge.description else "Procedimiento"
        allocation_rows.append(AllocationRow(description=label, amount=allocation.amount_applied))
        allocated_total += allocation.amount_applied

    return build_receipt_pdf(
        clinic_name=branding.display_name,
        logo=logo,
        patient_name=patient.full_name,
        payment_id=str(payment.id),
        method_label=PAYMENT_METHOD_LABELS[payment.method],
        reference=payment.reference,
        received_at_label=payment.received_at.strftime("%d/%m/%Y %H:%M"),
        amount=payment.amount,
        allocations=allocation_rows,
        unallocated_amount=payment.amount - allocated_total,
        received_by_name=received_by.full_name if received_by else "-",
    )


# -------------------------------------------------------------------------- resumen


async def get_patient_billing_summary(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    rows = await list_charges(db, clinic_id=clinic_id, patient_id=patient_id)
    total_charged = sum(
        (charge.amount for charge, _applied, _balance in rows if charge.is_active), Decimal("0.00")
    )
    total_paid = sum((applied for _charge, applied, _balance in rows), Decimal("0.00"))

    payments = await list_payments(db, clinic_id=clinic_id, patient_id=patient_id)
    total_received = sum((p.amount for p, _allocs in payments if p.is_active), Decimal("0.00"))
    total_credit = total_received - total_paid

    balance_due = max(total_charged - total_paid, Decimal("0.00"))
    return total_charged, total_paid, total_credit, balance_due


# ------------------------------------------------------------------------- caja


async def open_cash_session(
    db: AsyncSession, *, clinic_id: uuid.UUID, opening_amount: Decimal, actor_id: uuid.UUID
) -> CashSession:
    existing = await _get_open_cash_session(db, clinic_id=clinic_id)
    if existing is not None:
        raise AppError("CASH_SESSION_OPEN", "Ya hay una sesion de caja abierta", status_code=409)

    session = CashSession(
        clinic_id=clinic_id,
        opened_by=actor_id,
        opening_amount=opening_amount,
        status="ABIERTA",
        created_by=actor_id,
    )
    db.add(session)
    await db.flush()
    await audit_service.log(
        db,
        action="billing.cash_session_opened",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="cash_session",
        entity_id=str(session.id),
        details={"opening_amount": str(opening_amount)},
    )
    await db.commit()
    return session


async def _get_cash_session_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, session_id: uuid.UUID
) -> CashSession:
    session = await db.get(CashSession, session_id)
    if session is None or session.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Sesion de caja no encontrada", status_code=404)
    return session


async def cash_session_totals(db: AsyncSession, *, session_id: uuid.UUID) -> dict[str, Decimal]:
    stmt = select(Payment.method, Payment.amount).where(
        Payment.cash_session_id == session_id, Payment.is_active.is_(True)
    )
    totals: dict[str, Decimal] = dict.fromkeys(rules.PAYMENT_METHODS, Decimal("0.00"))
    for method, amount in (await db.execute(stmt)).all():
        totals[method] = totals.get(method, Decimal("0.00")) + amount
    return totals


async def get_cash_session(
    db: AsyncSession, *, clinic_id: uuid.UUID, session_id: uuid.UUID
) -> tuple[CashSession, dict[str, Decimal], Decimal, Decimal | None]:
    session = await _get_cash_session_in_clinic(db, clinic_id=clinic_id, session_id=session_id)
    totals = await cash_session_totals(db, session_id=session.id)
    expected_cash = session.opening_amount + totals["efectivo"]
    difference = (
        (session.closing_amount - expected_cash) if session.closing_amount is not None else None
    )
    return session, totals, expected_cash, difference


async def get_current_cash_session(
    db: AsyncSession, *, clinic_id: uuid.UUID
) -> tuple[CashSession, dict[str, Decimal], Decimal, Decimal | None] | None:
    session = await _get_open_cash_session(db, clinic_id=clinic_id)
    if session is None:
        return None
    return await get_cash_session(db, clinic_id=clinic_id, session_id=session.id)


async def close_cash_session(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    session_id: uuid.UUID,
    closing_amount: Decimal,
    notes: str | None,
    actor_id: uuid.UUID,
) -> tuple[CashSession, dict[str, Decimal], Decimal, Decimal | None]:
    session = await _get_cash_session_in_clinic(db, clinic_id=clinic_id, session_id=session_id)
    if session.status != "ABIERTA":
        raise AppError(
            "CASH_SESSION_CLOSED", "Esta sesion de caja ya esta cerrada", status_code=409
        )

    session.status = "CERRADA"
    session.closed_by = actor_id
    session.closed_at = datetime.now(UTC)
    session.closing_amount = closing_amount
    session.notes = notes

    totals = await cash_session_totals(db, session_id=session.id)
    expected_cash = session.opening_amount + totals["efectivo"]
    difference = closing_amount - expected_cash

    await audit_service.log(
        db,
        action="billing.cash_session_closed",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="cash_session",
        entity_id=str(session_id),
        details={
            "closing_amount": str(closing_amount),
            "expected_cash": str(expected_cash),
            "difference": str(difference),
        },
    )
    await db.commit()
    return session, totals, expected_cash, difference


# ----------------------------------------------------------------- configuracion


async def get_billing_settings(db: AsyncSession, *, clinic_id: uuid.UUID) -> bool:
    settings = await db.get(ClinicBillingSettings, clinic_id)
    return settings.billing_enabled if settings is not None else True


async def update_billing_settings(
    db: AsyncSession, *, clinic_id: uuid.UUID, billing_enabled: bool, actor_id: uuid.UUID
) -> bool:
    settings = await db.get(ClinicBillingSettings, clinic_id)
    if settings is None:
        settings = ClinicBillingSettings(clinic_id=clinic_id)
        db.add(settings)
    settings.billing_enabled = billing_enabled
    settings.updated_by = actor_id

    await audit_service.log(
        db,
        action="billing.settings_updated",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="clinic_billing_settings",
        entity_id=str(clinic_id),
        details={"billing_enabled": billing_enabled},
    )
    await db.commit()
    return settings.billing_enabled
