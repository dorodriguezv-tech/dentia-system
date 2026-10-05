import uuid
from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.agenda.rules import APPOINTMENT_STATUSES, APPOINTMENT_TYPE_CODES

AppointmentType = Literal[
    "consulta",
    "limpieza",
    "restauracion",
    "endodoncia",
    "extraccion",
    "ortodoncia_control",
    "protesis",
    "urgencia",
]
AppointmentStatus = Literal[
    "RESERVADA",
    "CONFIRMADA",
    "EN_SALA",
    "EN_ATENCION",
    "TERMINADA",
    "CANCELADA",
    "NO_SHOW",
    "REPROGRAMADA",
]


class ProviderCreateRequest(BaseModel):
    user_id: uuid.UUID
    color: str = Field(default="#2BB3A3", min_length=4, max_length=7)


class ProviderOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    color: str
    is_active: bool


class ResourceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ResourceOut(BaseModel):
    id: uuid.UUID
    name: str
    is_active: bool

    model_config = {"from_attributes": True}


class WorkingHoursCreateRequest(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time


class WorkingHoursOut(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    weekday: int
    start_time: time
    end_time: time

    model_config = {"from_attributes": True}


class BlockCreateRequest(BaseModel):
    starts_at: datetime
    ends_at: datetime
    reason: str | None = Field(default=None, max_length=300)


class BlockOut(BaseModel):
    id: uuid.UUID
    provider_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    reason: str | None

    model_config = {"from_attributes": True}


class AppointmentCreateRequest(BaseModel):
    patient_id: uuid.UUID
    provider_id: uuid.UUID
    resource_id: uuid.UUID | None = None
    appointment_type: AppointmentType
    starts_at: datetime
    ends_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=1000)


class AppointmentOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    provider_id: uuid.UUID
    resource_id: uuid.UUID | None
    appointment_type: AppointmentType
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    notes: str | None
    cancel_reason: str | None
    rescheduled_from_id: uuid.UUID | None
    warnings: list[str] = []

    model_config = {"from_attributes": True}


class AppointmentListItemOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    patient_full_name: str
    provider_id: uuid.UUID
    provider_full_name: str
    provider_color: str
    resource_id: uuid.UUID | None
    resource_name: str | None
    appointment_type: AppointmentType
    starts_at: datetime
    ends_at: datetime
    status: AppointmentStatus
    notes: str | None


class StatusChangeRequest(BaseModel):
    status: AppointmentStatus
    reason: str | None = Field(default=None, max_length=500)


class RescheduleRequest(BaseModel):
    starts_at: datetime
    ends_at: datetime | None = None
    provider_id: uuid.UUID | None = None
    resource_id: uuid.UUID | None = None
    reason: str | None = Field(default=None, max_length=500)


class WaitlistCreateRequest(BaseModel):
    patient_id: uuid.UUID
    provider_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=500)


class WaitlistOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    provider_id: uuid.UUID | None
    notes: str | None
    resolved: bool
    resolved_at: datetime | None

    model_config = {"from_attributes": True}


class ReminderTaskOut(BaseModel):
    id: uuid.UUID
    appointment_id: uuid.UUID
    kind: str
    scheduled_for: datetime
    status: str

    model_config = {"from_attributes": True}


def _validate_catalogs() -> None:
    assert set(APPOINTMENT_TYPE_CODES) == set(AppointmentType.__args__)  # type: ignore[attr-defined]
    assert set(APPOINTMENT_STATUSES) == set(AppointmentStatus.__args__)  # type: ignore[attr-defined]


_validate_catalogs()
