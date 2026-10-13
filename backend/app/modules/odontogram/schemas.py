import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.odontogram.rules import KINDS, ORIGINS, SURFACES

Surface = Literal["O", "M", "D", "V", "L", "P", "I"]
Kind = Literal["EXISTING", "PLANNED", "PERFORMED"]
Origin = Literal["MANUAL", "AI_ASSISTED"]
# B1 (Parte B, Fase 12.2): ya no es un Literal fijo -- "Hallazgos del odontograma"
# ahora vive en el catalogo administrable (app/modules/catalogs), validado contra la
# BD en el service (incluido si la pieza/superficie exige el hallazgo, campo
# `extra.requires_surface`), no por Pydantic.
FindingCode = str


class ToothFindingAnnulRequest(BaseModel):
    """B12 (docs/06_APP_MOVIL_V1_1_PARIDAD.md sec. 4, M5): anular con motivo
    obligatorio un hallazgo vigente que fue un error de captura -- distinto de
    "deshacer" (service.retire_finding, usado solo por el deshacer de 5 s de
    Dentia, Fase 13.3), que no pide motivo porque es inmediato tras capturarlo."""

    reason: str = Field(min_length=1, max_length=500)


class ToothFindingCreateRequest(BaseModel):
    patient_id: uuid.UUID
    encounter_id: uuid.UUID
    tooth_fdi: int
    surface: Surface | None = None
    finding_code: FindingCode = Field(min_length=1, max_length=60, pattern=r"^[a-z0-9_]+$")
    kind: Kind = "EXISTING"
    material: str | None = Field(default=None, max_length=100)


class ToothFindingOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    tooth_fdi: int
    surface: Surface | None
    finding_code: FindingCode
    kind: Kind
    material: str | None
    supersedes_id: uuid.UUID | None
    is_current: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


class ToothFindingHistoryEntryOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    tooth_fdi: int
    surface: Surface | None
    finding_code: FindingCode
    kind: Kind
    material: str | None
    supersedes_id: uuid.UUID | None
    is_current: bool
    origin: Origin
    created_at: datetime
    author_name: str


def _validate_catalogs() -> None:
    assert set(SURFACES) == set(Surface.__args__)  # type: ignore[attr-defined]
    assert set(KINDS) == set(Kind.__args__)  # type: ignore[attr-defined]
    assert set(ORIGINS) == set(Origin.__args__)  # type: ignore[attr-defined]


_validate_catalogs()
