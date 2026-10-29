import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.validators import Email
from app.modules.patients.rules import CONTACT_ROLES, PATIENT_TYPE_CODES, STATUS_CODES

StatusCode = Literal["activo", "inactivo", "referido", "fallecido", "bloqueado"]
ContactRole = Literal["guardian", "emergency", "other"]
SexCode = Literal["F", "M", "X"]
PatientTypeCode = Literal["pediatrico", "adulto"]


class ContactCreateRequest(BaseModel):
    role: ContactRole
    full_name: str = Field(min_length=1, max_length=200)
    relationship_label: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    email: Email | None = None
    # Alta de paciente pediatrico (CLAUDE.md): ocupacion del tutor/responsable, no del
    # paciente -- reemplaza al campo Patient.occupation que se oculta en ese caso.
    occupation: str | None = Field(default=None, max_length=150)


class ContactUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    relationship_label: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    email: Email | None = None
    occupation: str | None = Field(default=None, max_length=150)


class ContactOut(BaseModel):
    id: uuid.UUID
    role: ContactRole
    full_name: str
    relationship_label: str | None
    phone: str | None
    email: str | None
    occupation: str | None

    model_config = {"from_attributes": True}


class PatientCreateRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name_paternal: str = Field(min_length=1, max_length=100)
    last_name_maternal: str | None = Field(default=None, max_length=100)
    date_of_birth: date
    sex: SexCode | None = None
    # Anotacion del expediente (pendiente #73 de docs/PENDIENTES_CLINICOS.md): si se
    # omite o se manda None, el backend lo calcula a partir de date_of_birth
    # (patients/service.py); si se especifica, se respeta tal cual.
    patient_type: PatientTypeCode | None = None
    phone: str | None = Field(default=None, max_length=30)
    email: Email | None = None
    address: str | None = Field(default=None, max_length=300)
    # B3 (Parte B, Fase 12.2): gabinete y profesional tratante por defecto, opcionales
    # desde el alta -- la agenda los preselecciona despues al agendar.
    default_resource_id: uuid.UUID | None = None
    primary_provider_id: uuid.UUID | None = None
    # Fase A (rediseno del expediente, docs/clinica): campos compartidos que
    # autollenan la Historia Clinica General y demas documentos impresos.
    birth_place: str | None = Field(default=None, max_length=200)
    blood_type: str | None = Field(default=None, max_length=5)
    education_level: str | None = Field(default=None, max_length=50)
    can_read_write: bool | None = None
    religion: str | None = Field(default=None, max_length=100)
    ethnic_group: str | None = Field(default=None, max_length=100)
    race: str | None = Field(default=None, max_length=100)
    occupation: str | None = Field(default=None, max_length=150)
    marital_status: str | None = Field(default=None, max_length=30)

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
    # Igual criterio que en PatientCreateRequest: si se manda None (o se omite), no
    # se toca el valor ya guardado -- NO se recalcula automaticamente a partir de
    # date_of_birth (es una anotacion editable, no un campo 100% derivado). Solo se
    # sobreescribe cuando el usuario lo especifica explicitamente.
    patient_type: PatientTypeCode | None = None
    phone: str | None = Field(default=None, max_length=30)
    email: Email | None = None
    address: str | None = Field(default=None, max_length=300)
    status: StatusCode | None = None
    status_reason: str | None = Field(default=None, max_length=300)
    # B3 (Parte B, Fase 12.2): igual que el estado, cambiar el gabinete o el
    # profesional tratante por defecto exige un motivo (edicion controlada).
    default_resource_id: uuid.UUID | None = None
    primary_provider_id: uuid.UUID | None = None
    care_assignment_reason: str | None = Field(default=None, max_length=300)
    birth_place: str | None = Field(default=None, max_length=200)
    blood_type: str | None = Field(default=None, max_length=5)
    education_level: str | None = Field(default=None, max_length=50)
    can_read_write: bool | None = None
    religion: str | None = Field(default=None, max_length=100)
    ethnic_group: str | None = Field(default=None, max_length=100)
    race: str | None = Field(default=None, max_length=100)
    occupation: str | None = Field(default=None, max_length=150)
    marital_status: str | None = Field(default=None, max_length=30)

    @model_validator(mode="after")
    def _status_change_needs_reason(self) -> "PatientUpdateRequest":
        if self.status is not None and not (self.status_reason or "").strip():
            raise ValueError("status_reason es obligatorio al cambiar el estado del paciente")
        return self

    @model_validator(mode="after")
    def _care_assignment_change_needs_reason(self) -> "PatientUpdateRequest":
        if (self.default_resource_id is not None or self.primary_provider_id is not None) and not (
            self.care_assignment_reason or ""
        ).strip():
            raise ValueError(
                "care_assignment_reason es obligatorio al cambiar el gabinete o el "
                "profesional tratante por defecto"
            )
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
    patient_type: PatientTypeCode | None
    phone: str | None
    email: str | None
    address: str | None
    status: StatusCode
    has_photo: bool
    default_resource_id: uuid.UUID | None
    primary_provider_id: uuid.UUID | None
    birth_place: str | None
    blood_type: str | None
    education_level: str | None
    can_read_write: bool | None
    religion: str | None
    ethnic_group: str | None
    race: str | None
    occupation: str | None
    marital_status: str | None

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
    # B3 (Parte B, Fase 12.2): la agenda los usa para preseleccionar gabinete y
    # profesional en NewAppointmentForm.tsx al elegir un paciente por este buscador.
    default_resource_id: uuid.UUID | None = None
    primary_provider_id: uuid.UUID | None = None


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
    assert set(PATIENT_TYPE_CODES) == set(PatientTypeCode.__args__)  # type: ignore[attr-defined]


_validate_status_codes()
