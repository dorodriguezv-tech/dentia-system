import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.odontogram.schemas import FindingCode, Surface
from app.modules.treatment.rules import ACCEPTANCE_TYPES, ORIGINS, PLAN_STATUSES, PRIORITIES

PlanStatus = Literal["BORRADOR", "PRESENTADO", "ACEPTADO", "RECHAZADO", "EN_PROGRESO", "TERMINADO"]
Priority = Literal["alta", "media", "baja"]
AcceptanceType = Literal["TOTAL", "PARCIAL"]
Origin = Literal["MANUAL", "AI_ASSISTED"]


class ProcedureCatalogCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    default_price: Decimal = Field(ge=0)


class ProcedureCatalogOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    default_price: Decimal
    is_active: bool

    model_config = {"from_attributes": True}


class PlanCreateRequest(BaseModel):
    patient_id: uuid.UUID
    encounter_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class PlanOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    encounter_id: uuid.UUID
    professional_id: uuid.UUID
    title: str
    status: PlanStatus
    notes: str | None
    accepted_at: datetime | None
    accepted_by_name: str | None
    acceptance_type: AcceptanceType | None
    rejected_reason: str | None
    total: Decimal


class PhaseCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sort_order: int = 0
    priority: Priority = "media"


class ItemCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    tooth_fdi: int | None = None
    surface: Surface | None = None
    procedure_code: str = Field(min_length=1, max_length=50)
    finding_code: FindingCode | None = None
    quantity: int = Field(default=1, ge=1)
    alternative: str = Field(default="A", max_length=10)
    unit_price_override: Decimal | None = Field(default=None, ge=0)


class ItemOut(BaseModel):
    id: uuid.UUID
    phase_id: uuid.UUID
    encounter_id: uuid.UUID
    tooth_fdi: int | None
    surface: Surface | None
    procedure_code: str
    procedure_name: str
    finding_code: FindingCode | None
    unit_price: Decimal
    quantity: int
    alternative: str
    discount_amount: Decimal | None
    discount_reason: str | None
    accepted: bool
    is_active: bool
    origin: Origin
    subtotal: Decimal

    model_config = {"from_attributes": True}


class PhaseWithItemsOut(BaseModel):
    id: uuid.UUID
    name: str
    sort_order: int
    priority: Priority
    items: list[ItemOut]
    phase_total: Decimal


class PlanDetailOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    encounter_id: uuid.UUID
    professional_id: uuid.UUID
    title: str
    status: PlanStatus
    notes: str | None
    accepted_at: datetime | None
    accepted_by_name: str | None
    acceptance_type: AcceptanceType | None
    rejected_reason: str | None
    phases: list[PhaseWithItemsOut]
    total: Decimal


class DiscountRequest(BaseModel):
    amount: Decimal = Field(ge=0)
    reason: str = Field(min_length=1, max_length=500)


class AnnulRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class StatusChangeRequest(BaseModel):
    status: PlanStatus
    reason: str | None = Field(default=None, max_length=500)


class AcceptPlanRequest(BaseModel):
    accepted_item_ids: list[uuid.UUID] = Field(min_length=1)
    accepted_by_name: str = Field(min_length=1, max_length=200)


class ProcedurePerformedCreateRequest(BaseModel):
    patient_id: uuid.UUID
    encounter_id: uuid.UUID
    planned_id: uuid.UUID | None = None
    tooth_fdi: int | None = None
    surface: Surface | None = None
    procedure_code: str | None = Field(default=None, max_length=50)
    procedure_name: str | None = Field(default=None, max_length=200)
    finding_code: FindingCode | None = None
    material: str | None = Field(default=None, max_length=100)


class ProcedurePerformedOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    encounter_id: uuid.UUID
    planned_id: uuid.UUID | None
    tooth_fdi: int | None
    surface: Surface | None
    procedure_code: str
    procedure_name: str
    material: str | None
    performed_at: datetime
    origin: Origin
    charge_amount: Decimal

    model_config = {"from_attributes": True}


def _validate_catalogs() -> None:
    assert set(PLAN_STATUSES) == set(PlanStatus.__args__)  # type: ignore[attr-defined]
    assert set(PRIORITIES) == set(Priority.__args__)  # type: ignore[attr-defined]
    assert set(ACCEPTANCE_TYPES) == set(AcceptanceType.__args__)  # type: ignore[attr-defined]
    assert set(ORIGINS) == set(Origin.__args__)  # type: ignore[attr-defined]


_validate_catalogs()
