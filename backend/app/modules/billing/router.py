import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.core.storage import StorageBackend, get_storage_backend
from app.modules.billing import rules, service
from app.modules.billing.models import Charge, Payment, PaymentAllocation
from app.modules.billing.schemas import (
    AllocationOut,
    BillingSettingsOut,
    BillingSettingsUpdateRequest,
    CancelRequest,
    CashSessionCloseRequest,
    CashSessionOpenRequest,
    CashSessionOut,
    ChargeOut,
    PatientBillingSummaryOut,
    PaymentCreateRequest,
    PaymentOut,
)
from app.modules.iam.models import User

router = APIRouter(tags=["billing"])


def _charge_out(charge: Charge, applied: Decimal, balance: Decimal) -> ChargeOut:
    return ChargeOut(
        id=charge.id,
        patient_id=charge.patient_id,
        procedure_performed_id=charge.procedure_performed_id,
        amount=charge.amount,
        description=charge.description,
        is_active=charge.is_active,
        cancel_reason=charge.cancel_reason,
        computed_status=rules.charge_computed_status(
            is_active=charge.is_active, amount=charge.amount, applied=applied
        ),
        applied_amount=applied,
        balance=balance,
    )


def _payment_out(payment: Payment, allocations: list[PaymentAllocation]) -> PaymentOut:
    allocated = sum((a.amount_applied for a in allocations), Decimal("0.00"))
    return PaymentOut(
        id=payment.id,
        patient_id=payment.patient_id,
        method=payment.method,
        amount=payment.amount,
        received_at=payment.received_at,
        reference=payment.reference,
        notes=payment.notes,
        is_active=payment.is_active,
        cancel_reason=payment.cancel_reason,
        allocated_amount=allocated,
        unallocated_amount=payment.amount - allocated,
        allocations=[AllocationOut.model_validate(a) for a in allocations],
    )


@router.get("/patients/{patient_id}/charges", response_model=list[ChargeOut])
async def list_charges(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("billing.read")),
    db: AsyncSession = Depends(get_db),
) -> list[ChargeOut]:
    rows = await service.list_charges(db, clinic_id=clinic_id, patient_id=patient_id)
    return [_charge_out(charge, applied, balance) for charge, applied, balance in rows]


@router.post("/charges/{charge_id}/cancel", response_model=ChargeOut)
async def cancel_charge(
    charge_id: uuid.UUID,
    payload: CancelRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("billing.write")),
    db: AsyncSession = Depends(get_db),
) -> ChargeOut:
    charge = await service.cancel_charge(
        db, clinic_id=clinic_id, charge_id=charge_id, reason=payload.reason, actor_id=actor.id
    )
    return _charge_out(charge, Decimal("0.00"), Decimal("0.00"))


@router.get("/patients/{patient_id}/payments", response_model=list[PaymentOut])
async def list_payments(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("billing.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PaymentOut]:
    rows = await service.list_payments(db, clinic_id=clinic_id, patient_id=patient_id)
    return [_payment_out(payment, allocations) for payment, allocations in rows]


@router.post("/patients/{patient_id}/payments", response_model=PaymentOut, status_code=201)
async def create_payment(
    patient_id: uuid.UUID,
    payload: PaymentCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("billing.write")),
    db: AsyncSession = Depends(get_db),
) -> PaymentOut:
    payment, allocations = await service.create_payment(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return _payment_out(payment, allocations)


@router.get("/payments/{payment_id}/receipt")
async def get_receipt(
    payment_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("billing.read")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    pdf_bytes = await service.build_receipt(db, storage, clinic_id=clinic_id, payment_id=payment_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="recibo-{payment_id}.pdf"'},
    )


@router.post("/payments/{payment_id}/cancel", response_model=PaymentOut)
async def cancel_payment(
    payment_id: uuid.UUID,
    payload: CancelRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("billing.write")),
    db: AsyncSession = Depends(get_db),
) -> PaymentOut:
    payment, allocations = await service.cancel_payment(
        db, clinic_id=clinic_id, payment_id=payment_id, reason=payload.reason, actor_id=actor.id
    )
    return _payment_out(payment, allocations)


@router.get("/patients/{patient_id}/billing-summary", response_model=PatientBillingSummaryOut)
async def get_billing_summary(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("billing.read")),
    db: AsyncSession = Depends(get_db),
) -> PatientBillingSummaryOut:
    total_charged, total_paid, total_credit, balance_due = (
        await service.get_patient_billing_summary(db, clinic_id=clinic_id, patient_id=patient_id)
    )
    return PatientBillingSummaryOut(
        total_charged=total_charged,
        total_paid=total_paid,
        total_credit=total_credit,
        balance_due=balance_due,
    )


def _cash_session_out(session, totals, expected_cash, difference) -> CashSessionOut:  # type: ignore[no-untyped-def]
    return CashSessionOut(
        id=session.id,
        opened_at=session.opened_at,
        opening_amount=session.opening_amount,
        status=session.status,
        closed_at=session.closed_at,
        closing_amount=session.closing_amount,
        notes=session.notes,
        totals_by_method=totals,
        expected_cash=expected_cash,
        cash_difference=difference,
    )


@router.post("/cash-sessions/open", response_model=CashSessionOut, status_code=201)
async def open_cash_session(
    payload: CashSessionOpenRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("billing.write")),
    db: AsyncSession = Depends(get_db),
) -> CashSessionOut:
    session = await service.open_cash_session(
        db, clinic_id=clinic_id, opening_amount=payload.opening_amount, actor_id=actor.id
    )
    totals = await service.cash_session_totals(db, session_id=session.id)
    return _cash_session_out(session, totals, session.opening_amount, None)


@router.get("/cash-sessions/current", response_model=CashSessionOut | None)
async def get_current_cash_session(
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("billing.read")),
    db: AsyncSession = Depends(get_db),
) -> CashSessionOut | None:
    result = await service.get_current_cash_session(db, clinic_id=clinic_id)
    if result is None:
        return None
    return _cash_session_out(*result)


@router.get("/cash-sessions/{session_id}", response_model=CashSessionOut)
async def get_cash_session(
    session_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("billing.read")),
    db: AsyncSession = Depends(get_db),
) -> CashSessionOut:
    result = await service.get_cash_session(db, clinic_id=clinic_id, session_id=session_id)
    return _cash_session_out(*result)


@router.post("/cash-sessions/{session_id}/close", response_model=CashSessionOut)
async def close_cash_session(
    session_id: uuid.UUID,
    payload: CashSessionCloseRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("billing.write")),
    db: AsyncSession = Depends(get_db),
) -> CashSessionOut:
    result = await service.close_cash_session(
        db,
        clinic_id=clinic_id,
        session_id=session_id,
        closing_amount=payload.closing_amount,
        notes=payload.notes,
        actor_id=actor.id,
    )
    return _cash_session_out(*result)


@router.get("/billing/settings", response_model=BillingSettingsOut)
async def get_billing_settings(
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    # billing.read (no billing.configure): quien ve cargos/pagos tambien necesita saber
    # si la cobranza esta activa para decidir si mostrar la pestana "Cuenta" -- solo
    # cambiarlo (PUT) se queda en billing.configure.
    _actor: User = Depends(require_permission("billing.read")),
    db: AsyncSession = Depends(get_db),
) -> BillingSettingsOut:
    enabled = await service.get_billing_settings(db, clinic_id=clinic_id)
    return BillingSettingsOut(billing_enabled=enabled)


@router.put("/billing/settings", response_model=BillingSettingsOut)
async def update_billing_settings(
    payload: BillingSettingsUpdateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("billing.configure")),
    db: AsyncSession = Depends(get_db),
) -> BillingSettingsOut:
    enabled = await service.update_billing_settings(
        db, clinic_id=clinic_id, billing_enabled=payload.billing_enabled, actor_id=actor.id
    )
    return BillingSettingsOut(billing_enabled=enabled)
