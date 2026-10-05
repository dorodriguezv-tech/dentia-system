import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.imaging.rules import STUDY_TYPES

StudyType = Literal[
    "intraoral", "extraoral", "periapical", "bitewing", "panoramica", "cefalometria"
]


class ImageOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    study_type: StudyType
    tooth_fdi: int | None
    procedure_planned_id: uuid.UUID | None
    procedure_performed_id: uuid.UUID | None
    content_type: str
    original_filename: str
    notes: str | None
    has_thumbnail: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AnnulRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


def _validate_catalogs() -> None:
    assert set(STUDY_TYPES) == set(StudyType.__args__)  # type: ignore[attr-defined]


_validate_catalogs()
