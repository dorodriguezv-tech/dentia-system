import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.odontological_history.rules import (
    KENNEDY_CLASSES,
    ORAL_HEALTH_SELF_PERCEPTION_LEVELS,
    ORIGINS,
    PERIODONTAL_ANAMNESIS_ANSWER_VALUES,
)

Origin = Literal["MANUAL", "AI_ASSISTED"]
# Catalogos administrables (app.modules.catalogs): no son Literal fijo, se
# validan contra la BD en el service (igual que "pathological_condition" de
# Fase A).
SkullType = str
FacialBiotype = str
KennedyClass = Literal["I", "II", "III"]
PeriodontalAnswer = Literal["si", "no", "no_recuerda"]
OralHealthSelfPerception = Literal["buena", "regular", "mala"]


class AnnulRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


# --------------------------------------------------------------------------------
# 1. Exploracion cabeza/cuello + biotipo facial + ATM + tejidos blandos.
# --------------------------------------------------------------------------------


class OdontologicalExamCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    skull_type: SkullType | None = Field(default=None, max_length=40)
    facial_biotype: FacialBiotype | None = Field(default=None, max_length=40)
    facial_biotype_observations: str | None = Field(default=None, max_length=2000)

    apertura_conservada_mm: float | None = Field(default=None, ge=0, le=100)
    apertura_limitada_mm: float | None = Field(default=None, ge=0, le=100)
    chasquidos_derecho: bool = False
    crepitacion_derecho: bool = False
    chasquidos_izquierdo: bool = False
    crepitacion_izquierdo: bool = False
    dolor_apertura_lateralidad: bool = False
    fatiga_dolor_muscular: bool = False
    desviacion_apertura_cierre: bool = False
    atm_observaciones: str | None = Field(default=None, max_length=2000)

    ganglios: str | None = Field(default=None, max_length=2000)
    carrillos: str | None = Field(default=None, max_length=2000)
    labios: str | None = Field(default=None, max_length=2000)
    lengua: str | None = Field(default=None, max_length=2000)
    piso_boca: str | None = Field(default=None, max_length=2000)
    region_retromolar: str | None = Field(default=None, max_length=2000)
    paladar_duro_blando: str | None = Field(default=None, max_length=2000)
    faringe: str | None = Field(default=None, max_length=2000)
    encia_libre_marginal: str | None = Field(default=None, max_length=2000)
    tejidos_blandos_observaciones: str | None = Field(default=None, max_length=2000)


class OdontologicalExamOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    skull_type: SkullType | None
    facial_biotype: FacialBiotype | None
    facial_biotype_observations: str | None
    apertura_conservada_mm: float | None
    apertura_limitada_mm: float | None
    chasquidos_derecho: bool
    crepitacion_derecho: bool
    chasquidos_izquierdo: bool
    crepitacion_izquierdo: bool
    dolor_apertura_lateralidad: bool
    fatiga_dolor_muscular: bool
    desviacion_apertura_cierre: bool
    atm_observaciones: str | None
    ganglios: str | None
    carrillos: str | None
    labios: str | None
    lengua: str | None
    piso_boca: str | None
    region_retromolar: str | None
    paladar_duro_blando: str | None
    faringe: str | None
    encia_libre_marginal: str | None
    tejidos_blandos_observaciones: str | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 2. Anamnesis periodontal.
# --------------------------------------------------------------------------------


class PeriodontalAnamnesisCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    # {codigo_pregunta: "si"|"no"|"no_recuerda"}, codigo validado contra el
    # catalogo administrable "periodontal_anamnesis_question".
    answers: dict[str, PeriodontalAnswer] = Field(default_factory=dict)

    cepillado_veces_dia: int | None = Field(default=None, ge=0, le=20)
    cepillado_pasta: str | None = Field(default=None, max_length=200)
    insatisfaccion_motivo: str | None = Field(default=None, max_length=300)
    tratamiento_medico_detalle: str | None = Field(default=None, max_length=300)
    medicamento_actual: str | None = Field(default=None, max_length=300)
    cirugia_detalle: str | None = Field(default=None, max_length=300)
    hormonas_para_que: str | None = Field(default=None, max_length=300)
    habito_danino_cual: str | None = Field(default=None, max_length=300)
    fuma_cigarros_dia: int | None = Field(default=None, ge=0, le=200)
    alcohol_veces_semana: int | None = Field(default=None, ge=0, le=100)
    ultimo_examen_odontologico: str | None = Field(default=None, max_length=100)
    salud_bucal_autopercibida: OralHealthSelfPerception | None = None


class PeriodontalAnamnesisOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    answers: dict[str, str]
    cepillado_veces_dia: int | None
    cepillado_pasta: str | None
    insatisfaccion_motivo: str | None
    tratamiento_medico_detalle: str | None
    medicamento_actual: str | None
    cirugia_detalle: str | None
    hormonas_para_que: str | None
    habito_danino_cual: str | None
    fuma_cigarros_dia: int | None
    alcohol_veces_semana: int | None
    ultimo_examen_odontologico: str | None
    salud_bucal_autopercibida: OralHealthSelfPerception | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 3. Auxiliares de diagnostico -- analisis radiografico.
# --------------------------------------------------------------------------------


class RadiographicFindingDetail(BaseModel):
    organos_dentarios: str = Field(min_length=1, max_length=200)
    porcentaje: str | None = Field(default=None, max_length=50)
    alteracion: str | None = Field(default=None, max_length=300)


class RadiographicAnalysisCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    # {tipo: {...}}, tipo uno de los 5 fijos de rules.RADIOGRAPHIC_FINDING_TYPES.
    findings: dict[str, RadiographicFindingDetail] = Field(default_factory=dict)
    anexos_nota: str | None = Field(default=None, max_length=1000)


class RadiographicAnalysisOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    findings: dict[str, RadiographicFindingDetail]
    anexos_nota: str | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 4. Odontograma de diagnostico -- datos complementarios.
# --------------------------------------------------------------------------------


class FixedProsthesisEntry(BaseModel):
    tooth_fdi: str = Field(min_length=2, max_length=2)
    cr_relation: str = Field(min_length=1, max_length=200)


class OdontogramDiagnosisDetailCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    edentulous_space_available: bool | None = None
    edentulous_space_comments: str | None = Field(default=None, max_length=500)
    kennedy_sup_class: KennedyClass | None = None
    kennedy_sup_modification: bool = False
    kennedy_inf_class: KennedyClass | None = None
    kennedy_inf_modification: bool = False
    fixed_prosthesis_analysis: list[FixedProsthesisEntry] = Field(default_factory=list)


class OdontogramDiagnosisDetailOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    edentulous_space_available: bool | None
    edentulous_space_comments: str | None
    kennedy_sup_class: KennedyClass | None
    kennedy_sup_modification: bool
    kennedy_inf_class: KennedyClass | None
    kennedy_inf_modification: bool
    fixed_prosthesis_analysis: list[FixedProsthesisEntry]
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 5. Analisis con paralelometro.
# --------------------------------------------------------------------------------


class ParallelometerEntry(BaseModel):
    organo_dental: str = Field(min_length=1, max_length=50)
    caracteristicas: str = Field(min_length=1, max_length=500)
    plan_tratamiento: str = Field(min_length=1, max_length=500)


class ParallelometerAnalysisCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    entries: list[ParallelometerEntry] = Field(default_factory=list)


class ParallelometerAnalysisOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    entries: list[ParallelometerEntry]
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 6. Diseno de protesis parcial removible.
# --------------------------------------------------------------------------------


class RemovablePartialDentureDesignCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    conector_mayor: str | None = Field(default=None, max_length=300)
    conector_menor: str | None = Field(default=None, max_length=300)
    retenedores_directos: str | None = Field(default=None, max_length=300)
    conectores_indirectos: str | None = Field(default=None, max_length=300)
    base_protesica: str | None = Field(default=None, max_length=300)
    dientes_artificiales: str | None = Field(default=None, max_length=300)


class RemovablePartialDentureDesignOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    conector_mayor: str | None
    conector_menor: str | None
    retenedores_directos: str | None
    conectores_indirectos: str | None
    base_protesica: str | None
    dientes_artificiales: str | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 7/8. Diagnostico y plan de tratamiento por organo dental.
# --------------------------------------------------------------------------------


class ToothDiagnosisEntryCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    # {tooth_fdi: texto}, claves validadas contra piezas FDI permanentes.
    diagnoses: dict[str, str] = Field(default_factory=dict)
    observaciones: str | None = Field(default=None, max_length=1000)


class ToothDiagnosisEntryOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    diagnoses: dict[str, str]
    observaciones: str | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


class ToothTreatmentPlanEntryCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    plans: dict[str, str] = Field(default_factory=dict)
    observaciones: str | None = Field(default=None, max_length=1000)


class ToothTreatmentPlanEntryOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    plans: dict[str, str]
    observaciones: str | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


def _validate_catalogs() -> None:
    assert set(ORIGINS) == set(Origin.__args__)  # type: ignore[attr-defined]
    assert set(KENNEDY_CLASSES) == set(KennedyClass.__args__)  # type: ignore[attr-defined]
    assert set(PERIODONTAL_ANAMNESIS_ANSWER_VALUES) == set(
        PeriodontalAnswer.__args__  # type: ignore[attr-defined]
    )
    assert set(ORAL_HEALTH_SELF_PERCEPTION_LEVELS) == set(
        OralHealthSelfPerception.__args__  # type: ignore[attr-defined]
    )


_validate_catalogs()
