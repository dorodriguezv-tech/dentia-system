import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.records.rules import ORIGINS, SEVERITY_LEVELS

# B1 (Parte B, Fase 12.2): ya no es un Literal fijo -- "Categorias de antecedentes"
# ahora vive en el catalogo administrable (app/modules/catalogs), validado contra la
# BD en el service, no por Pydantic.
HistoryCategory = str
Severity = Literal["leve", "moderada", "severa"]
Origin = Literal["MANUAL", "AI_ASSISTED"]


class MedicalHistoryCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    category: HistoryCategory = Field(min_length=1, max_length=60, pattern=r"^[a-z0-9_]+$")
    text: str = Field(min_length=1, max_length=2000)


class MedicalHistoryOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    category: HistoryCategory
    text: str
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


class AllergyCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    substance: str = Field(min_length=1, max_length=200)
    reaction: str | None = Field(default=None, max_length=300)
    severity: Severity


class AllergyOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    substance: str
    reaction: str | None
    severity: Severity
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


class MedicationCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    name: str = Field(min_length=1, max_length=200)
    dose: str | None = Field(default=None, max_length=100)
    frequency: str | None = Field(default=None, max_length=100)


class MedicationOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    name: str
    dose: str | None
    frequency: str | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


class VitalSignsCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    bp_systolic: int | None = Field(default=None, ge=40, le=260)
    bp_diastolic: int | None = Field(default=None, ge=20, le=200)
    heart_rate: int | None = Field(default=None, ge=20, le=250)
    temperature: float | None = Field(default=None, ge=30, le=43)


class VitalSignsOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    recorded_at: datetime
    bp_systolic: int | None
    bp_diastolic: int | None
    heart_rate: int | None
    temperature: float | None
    origin: Origin

    model_config = {"from_attributes": True}


class AnnulRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


def _validate_catalogs() -> None:
    assert set(SEVERITY_LEVELS) == set(Severity.__args__)  # type: ignore[attr-defined]
    assert set(ORIGINS) == set(Origin.__args__)  # type: ignore[attr-defined]


_validate_catalogs()
