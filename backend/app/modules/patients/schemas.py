import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.validators import Email
from app.modules.patients.rules import CONTACT_ROLES, STATUS_CODES

StatusCode = Literal["activo", "inactivo", "referido", "fallecido", "bloqueado"]
ContactRole = Literal["guardian", "emergency", "other"]
SexCode = Literal["F", "M", "X"]


class ContactCreateRequest(BaseModel):
    role: ContactRole
    full_name: str = Field(min_length=1, max_length=200)
    relationship_label: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    email: Email | None = None


class ContactUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    relationship_label: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    email: Email | None = None


class ContactOut(BaseModel):
    id: uuid.UUID
    role: ContactRole
    full_name: str
    relationship_label: str | None
    phone: str | None
    email: str | None

    model_config = {"from_attributes": True}


class PatientCreateRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name_paternal: str = Field(min_length=1, max_length=100)
    last_name_maternal: str | None = Field(default=None, max_length=100)
    date_of_birth: date
    sex: SexCode | None = None
    phone: str | None = Field(default=None, max_length=30)
    email: Email | None = None
    address: str | None = Field(default=None, max_length=300)

    @field_validator("date_of_birth")
    @classmethod
    def _not_in_the_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("La fecha de nacimiento no puede ser futura")
        return value


class PatientUpdateRequest(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name_paternal: str | None = Field(default=None, min_length=1, max_length=100)
    last_name_maternal: str | None = Field(default=None, max_length=100)
    sex: SexCode | None = None
    phone: str | None = Field(default=None, max_length=30)
    email: Email | None = None
    address: str | None = Field(default=None, max_length=300)
    status: StatusCode | None = None
    status_reason: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _status_change_needs_reason(self) -> "PatientUpdateRequest":
        if self.status is not None and not (self.status_reason or "").strip():
            raise ValueError("status_reason es obligatorio al cambiar el estado del paciente")
        return self


class PatientOut(BaseModel):
    id: uuid.UUID
    expediente_number: str
    first_name: str
    last_name_paternal: str
    last_name_maternal: str | None
    full_name: str
    date_of_birth: date
    sex: SexCode | None
    phone: str | None
    email: str | None
    address: str | None
    status: StatusCode
    has_photo: bool

    model_config = {"from_attributes": True}


class PatientSummaryOut(BaseModel):
    id: uuid.UUID
    expediente_number: str
    full_name: str
    age: int
    status: StatusCode
    has_photo: bool
    alerts: list[str] = Field(default_factory=list)


class PatientListItemOut(BaseModel):
    id: uuid.UUID
    expediente_number: str
    full_name: str
    date_of_birth: date
    status: StatusCode
    phone: str | None


class DuplicateCheckRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name_paternal: str = Field(min_length=1, max_length=100)
    last_name_maternal: str | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None
    phone: str | None = Field(default=None, max_length=30)


class DuplicateCandidateOut(BaseModel):
    id: uuid.UUID
    expediente_number: str
    full_name: str
    date_of_birth: date
    phone: str | None
    similarity: float


def _validate_status_codes() -> None:
    assert set(STATUS_CODES) == set(StatusCode.__args__)  # type: ignore[attr-defined]
    assert set(CONTACT_ROLES) == set(ContactRole.__args__)  # type: ignore[attr-defined]


_validate_status_codes()
