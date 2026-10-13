import uuid
from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.agenda.rules import APPOINTMENT_STATUSES

# B1 (Parte B, Fase 12.2): ya no es un Literal fijo -- "Tipos de consulta/cita" ahora
# vive en el catalogo administrable (app/modules/catalogs), validado contra la BD en
# el service, no por Pydantic. Sigue siendo un string acotado al mismo formato de
# codigo que el resto de los catalogos (minusculas, numeros y guion bajo).
AppointmentType = str
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
    # B2 (Parte B, Fase 12.2): gabinete que la agenda preselecciona al agendar con
    # este profesional en esta sucursal (opcional).
    default_resource_id: uuid.UUID | None = None


class ProviderOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    color: str
    is_active: bool
    default_resource_id: uuid.UUID | None = None


class ResourceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ResourceUpdateRequest(BaseModel):
    """Pendiente de B1 (Parte B, Fase 12.2): administrar Gabinetes desde la
    pantalla de Catalogos -- antes no habia forma de renombrar ni desactivar uno."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


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
    appointment_type: AppointmentType = Field(min_length=1, max_length=60, pattern=r"^[a-z0-9_]+$")
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


class AvailableSlotsOut(BaseModel):
    """B8 (docs/06_APP_MOVIL_V1_1_PARIDAD.md sec. 4): huecos libres reales de un
    profesional en un dia, para que la app no tenga que calcularlos -- la misma
    logica que ya usaba Dentia por voz (service.find_free_slots)."""

    slots: list[datetime]


class DayScheduleSlotOut(BaseModel):
    """Una hora completa de la agenda de un profesional: disponible u ocupada."""

    starts_at: datetime
    available: bool


class DayScheduleOut(BaseModel):
    """Cuadricula de horas completas del dia (9:00, 10:00, ...) para elegir un
    horario tocando en vez de escribirlo -- reporte de uso en telefono real: la
    app solo mostraba 3 huecos libres dispersos en pasos de 15 minutos."""

    slots: list[DayScheduleSlotOut]


class ReminderTaskOut(BaseModel):
    id: uuid.UUID
    appointment_id: uuid.UUID
    kind: str
    scheduled_for: datetime
    status: str

    model_config = {"from_attributes": True}


def _validate_catalogs() -> None:
    assert set(APPOINTMENT_STATUSES) == set(AppointmentStatus.__args__)  # type: ignore[attr-defined]


_validate_catalogs()
