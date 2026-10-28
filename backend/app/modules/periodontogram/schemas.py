import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.periodontogram.rules import (
    FURCATION_GRADE_MAX,
    FURCATION_GRADE_MIN,
    INDEX_GRADE_MAX,
    INDEX_GRADE_MIN,
    MOBILITY_GRADE_MAX,
    MOBILITY_GRADE_MIN,
    ORIGINS,
    PROBING_DEPTH_MM_MAX,
    PROBING_DEPTH_MM_MIN,
    RECESSION_MM_MAX,
    RECESSION_MM_MIN,
)

Origin = Literal["MANUAL", "AI_ASSISTED"]
# 6 sitios estandar de sondeo (ver rules.PROBING_SITES/PROBING_SITE_LABELS).
ProbingSite = Literal[
    "mesiovestibular",
    "vestibular",
    "distovestibular",
    "mesiolingual",
    "lingual",
    "distolingual",
]
IndexType = Literal["placa", "gingival"]
IndexSurface = Literal["vestibular", "lingual"]
OcclusalMovement = Literal["centrica", "lateralidad_izquierda", "protrusion", "lateralidad_derecha"]


class AnnulRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


# --------------------------------------------------------------------------------
# 1. Sondeo periodontal -- 6 sitios por pieza.
# --------------------------------------------------------------------------------


class PeriodontalProbingSiteCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    tooth_fdi: str = Field(min_length=2, max_length=2)
    site: ProbingSite
    probing_depth_mm: int = Field(ge=PROBING_DEPTH_MM_MIN, le=PROBING_DEPTH_MM_MAX)
    recession_mm: int = Field(ge=RECESSION_MM_MIN, le=RECESSION_MM_MAX)
    bleeding_on_probing: bool = False
    suppuration: bool = False


class PeriodontalProbingSiteOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    tooth_fdi: str
    site: ProbingSite
    probing_depth_mm: int
    recession_mm: int
    bleeding_on_probing: bool
    suppuration: bool
    # Calculado al vuelo por el router (nunca persistido), mismo criterio que
    # el IMC de la Fase A -- ver rules.clinical_attachment_level_mm.
    clinical_attachment_level_mm: int | None = None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 2. Medicion por pieza -- movilidad y furcacion.
# --------------------------------------------------------------------------------


class PeriodontalToothMeasurementCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    tooth_fdi: str = Field(min_length=2, max_length=2)
    mobility_grade: int | None = Field(default=None, ge=MOBILITY_GRADE_MIN, le=MOBILITY_GRADE_MAX)
    furcation_grade: int | None = Field(
        default=None, ge=FURCATION_GRADE_MIN, le=FURCATION_GRADE_MAX
    )


class PeriodontalToothMeasurementOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    tooth_fdi: str
    mobility_grade: int | None
    furcation_grade: int | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 3. Indices de placa dentobacteriana y gingival.
# --------------------------------------------------------------------------------


class PeriodontalIndexEntryCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    tooth_fdi: str = Field(min_length=2, max_length=2)
    index_type: IndexType
    surface: IndexSurface
    grade: int = Field(ge=INDEX_GRADE_MIN, le=INDEX_GRADE_MAX)


class PeriodontalIndexEntryOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    tooth_fdi: str
    index_type: IndexType
    surface: IndexSurface
    grade: int
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


class PlaqueIndexSummary(BaseModel):
    numero_caras_totales: int
    numero_caras_pigmentadas: int
    indice_placa_dentobacteriana: float | None


class GingivalIndexSummary(BaseModel):
    numero_sitios_totales: int
    indice_gingival_total: float | None


class IndicesSummaryOut(BaseModel):
    """Resumen de indices calculados al vuelo (no persistidos) para un
    encounter: el mas reciente con datos activos si no se especifica
    `encounter_id`, ver service.py::get_indices_summary."""

    encounter_id: uuid.UUID | None
    placa: PlaqueIndexSummary
    gingival: GingivalIndexSummary


# --------------------------------------------------------------------------------
# 4. Tablas de oclusion -- contactos marcados.
# --------------------------------------------------------------------------------


class OcclusalContactEntryCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    tooth_fdi: str = Field(min_length=2, max_length=2)
    movement: OcclusalMovement


class OcclusalContactEntryOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    tooth_fdi: str
    movement: OcclusalMovement
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 5. Observaciones del periodontograma.
# --------------------------------------------------------------------------------


class PeriodontogramObservationCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    observaciones: str | None = Field(default=None, max_length=2000)


class PeriodontogramObservationOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    observaciones: str | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


def _validate_catalogs() -> None:
    assert set(ORIGINS) == set(Origin.__args__)  # type: ignore[attr-defined]


_validate_catalogs()
