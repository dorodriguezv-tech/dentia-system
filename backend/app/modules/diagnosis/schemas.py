import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.diagnosis.rules import ORIGINS
from app.modules.odontogram.schemas import Surface

Origin = Literal["MANUAL", "AI_ASSISTED"]

# B1 (Parte B, Fase 12.2): ya no es un Literal fijo -- "Diagnosticos" ahora vive en el
# catalogo administrable (app/modules/catalogs), validado contra la BD en el service
# cuando se manda (sigue siendo opcional: el texto del diagnostico siempre es libre).
DiagnosisCode = str


class DiagnosisCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    tooth_fdi: int | None = None
    surface: Surface | None = None
    code: DiagnosisCode | None = Field(
        default=None, min_length=1, max_length=60, pattern=r"^[a-z0-9_]+$"
    )
    text: str = Field(min_length=1, max_length=2000)


class DiagnosisOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    professional_id: uuid.UUID
    tooth_fdi: int | None
    surface: Surface | None
    code: DiagnosisCode | None
    text: str
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


class AnnulRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


def _validate_catalogs() -> None:
    assert set(ORIGINS) == set(Origin.__args__)  # type: ignore[attr-defined]


_validate_catalogs()
