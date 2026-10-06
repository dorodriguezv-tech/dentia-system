import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.billing.rules import CASH_SESSION_STATUSES, CHARGE_STATUSES, PAYMENT_METHODS

PaymentMethod = Literal["efectivo", "tarjeta", "transferencia"]
ChargeStatus = Literal["PENDIENTE", "PARCIAL", "PAGADO", "CANCELADO"]
CashSessionStatus = Literal["ABIERTA", "CERRADA"]


class ChargeOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    procedure_performed_id: uuid.UUID
    amount: Decimal
    description: str | None
    is_active: bool
    cancel_reason: str | None
    computed_status: ChargeStatus
    applied_amount: Decimal
    balance: Decimal

    model_config = {"from_attributes": True}


class CancelRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class AllocationInput(BaseModel):
    charge_id: uuid.UUID
    amount: Decimal = Field(gt=0)


class PaymentCreateRequest(BaseModel):
    method: PaymentMethod
    amount: Decimal = Field(gt=0)
    reference: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)
    allocations: list[AllocationInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def _allocations_do_not_exceed_amount(self) -> "PaymentCreateRequest":
        total = sum((a.amount for a in self.allocations), Decimal("0.00"))
        if total > self.amount:
            raise ValueError("La suma de las aplicaciones no puede superar el monto del pago")
        return self


class AllocationOut(BaseModel):
    id: uuid.UUID
    charge_id: uuid.UUID
    amount_applied: Decimal

    model_config = {"from_attributes": True}


class PaymentOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    method: PaymentMethod
    amount: Decimal
    received_at: datetime
    reference: str | None
    notes: str | None
    is_active: bool
    cancel_reason: str | None
    allocated_amount: Decimal
    unallocated_amount: Decimal
    allocations: list[AllocationOut]

    model_config = {"from_attributes": True}


class PatientBillingSummaryOut(BaseModel):
    total_charged: Decimal
    total_paid: Decimal
    total_credit: Decimal
    balance_due: Decimal


class CashSessionOpenRequest(BaseModel):
    opening_amount: Decimal = Field(ge=0)


class CashSessionCloseRequest(BaseModel):
    closing_amount: Decimal = Field(ge=0)
    notes: str | None = Field(default=None, max_length=500)


class CashSessionOut(BaseModel):
    id: uuid.UUID
    opened_at: datetime
    opening_amount: Decimal
    status: CashSessionStatus
    closed_at: datetime | None
    closing_amount: Decimal | None
    notes: str | None
    totals_by_method: dict[str, Decimal]
    expected_cash: Decimal
    cash_difference: Decimal | None

    model_config = {"from_attributes": True}


class BillingSettingsOut(BaseModel):
    billing_enabled: bool


class BillingSettingsUpdateRequest(BaseModel):
    billing_enabled: bool


def _validate_catalogs() -> None:
    assert set(PAYMENT_METHODS) == set(PaymentMethod.__args__)  # type: ignore[attr-defined]
    assert set(CHARGE_STATUSES) == set(ChargeStatus.__args__)  # type: ignore[attr-defined]
    assert set(CASH_SESSION_STATUSES) == set(CashSessionStatus.__args__)  # type: ignore[attr-defined]


_validate_catalogs()
