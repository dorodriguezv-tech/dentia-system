import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.odontogram.finding_catalog import FINDING_CODES
from app.modules.odontogram.rules import KINDS, ORIGINS, SURFACES

Surface = Literal["O", "M", "D", "V", "L", "P", "I"]
Kind = Literal["EXISTING", "PLANNED", "PERFORMED"]
Origin = Literal["MANUAL", "AI_ASSISTED"]
FindingCode = Literal[
    "sano",
    "caries",
    "restauracion",
    "corona",
    "endodoncia",
    "ausente",
    "extraccion_indicada",
    "implante",
    "protesis_fija",
    "sellador",
    "fractura",
    "movilidad",
]


class ToothFindingCreateRequest(BaseModel):
    patient_id: uuid.UUID
    encounter_id: uuid.UUID
    tooth_fdi: int
    surface: Surface | None = None
    finding_code: FindingCode
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
    assert set(FINDING_CODES) == set(FindingCode.__args__)  # type: ignore[attr-defined]


_validate_catalogs()
