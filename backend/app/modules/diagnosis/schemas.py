import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.diagnosis.rules import DIAGNOSIS_CODES
from app.modules.odontogram.schemas import Surface

DiagnosisCode = Literal[
    "caries",
    "caries_recurrente",
    "pulpitis_reversible",
    "pulpitis_irreversible",
    "necrosis_pulpar",
    "absceso_periapical",
    "gingivitis",
    "periodontitis",
    "fractura_dental",
    "edentulismo_parcial",
    "maloclusion",
    "sin_hallazgos",
]


class DiagnosisCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    tooth_fdi: int | None = None
    surface: Surface | None = None
    code: DiagnosisCode | None = None
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
    created_at: datetime

    model_config = {"from_attributes": True}


class AnnulRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


def _validate_catalogs() -> None:
    assert set(DIAGNOSIS_CODES) == set(DiagnosisCode.__args__)  # type: ignore[attr-defined]


_validate_catalogs()
