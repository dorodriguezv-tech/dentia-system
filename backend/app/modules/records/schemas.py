import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.records.rules import (
    BLEEDING_GUMS_LEVELS,
    FAMILY_STATUSES,
    FOOD_QUALITY_LEVELS,
    GLUCOSE_TIMINGS,
    HEALTH_COVERAGE_TYPES,
    ORIGINS,
    PATIENT_ATTITUDES,
    SEVERITY_LEVELS,
)

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


GlucoseTiming = Literal["postprandial", "preprandial"]
PatientAttitude = Literal["cooperador", "no_cooperador"]


class VitalSignsCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    bp_systolic: int | None = Field(default=None, ge=40, le=260)
    bp_diastolic: int | None = Field(default=None, ge=20, le=200)
    heart_rate: int | None = Field(default=None, ge=20, le=250)
    temperature: float | None = Field(default=None, ge=30, le=43)
    # Fase A (rediseno del expediente, docs/clinica): campos nuevos del formato
    # de signos vitales de la Historia Clinica General.
    height_m: float | None = Field(default=None, gt=0, le=2.5)
    weight_kg: float | None = Field(default=None, gt=0, le=400)
    spo2: int | None = Field(default=None, ge=0, le=100)
    glucose_index: float | None = Field(default=None, ge=0, le=999)
    glucose_timing: GlucoseTiming | None = None
    patient_attitude: PatientAttitude | None = None
    asa_classification: str | None = Field(default=None, max_length=10)


class VitalSignsOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    recorded_at: datetime
    bp_systolic: int | None
    bp_diastolic: int | None
    heart_rate: int | None
    temperature: float | None
    height_m: float | None
    weight_kg: float | None
    spo2: int | None
    glucose_index: float | None
    glucose_timing: GlucoseTiming | None
    patient_attitude: PatientAttitude | None
    asa_classification: str | None
    body_mass_index: float | None = None
    origin: Origin

    model_config = {"from_attributes": True}


class AnnulRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


# --------------------------------------------------------------------------------
# Fase A (rediseno del expediente, docs/clinica): Historia Clinica General.
# --------------------------------------------------------------------------------

FamilyRelationship = str  # catalogo administrable "family_relationship"
FamilyStatus = Literal["en_vida", "fallecido"]
BleedingGumsLevel = Literal["nunca", "algunas_veces", "siempre"]
FoodQualityLevel = Literal["buena", "mala", "regular"]
HealthCoverageType = Literal["civil", "derechohabiente", "militar"]
# Corrección Fase A: dejo de ser un catalogo cerrado -- el formulario ofrece
# MARITAL_STATUSES (rules.py) como sugerencias mas "Otro" con texto libre a
# teclear, asi que el backend solo valida longitud, no un conjunto fijo.
MaritalStatus = str


class FamilyHistoryEntryCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    relationship_code: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_]+$")
    status: FamilyStatus
    conditions: dict[str, bool] = Field(default_factory=dict)


class FamilyHistoryEntryOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    relationship_code: str
    status: FamilyStatus
    conditions: dict[str, bool]
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


class PersonalPathologicalHistoryCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    dolor_masticar: bool = False
    sensibilidad_frio: bool = False
    sensibilidad_calor: bool = False
    sensibilidad_dulce: bool = False
    sensibilidad_localizacion: str | None = Field(default=None, max_length=200)
    sangrado_encias: BleedingGumsLevel = "nunca"
    dolor_cepillado: bool = False
    aftas_ulceras: bool = False
    perdida_piezas: bool = False
    perdida_piezas_causa: str | None = Field(default=None, max_length=300)
    anestesia_previa: bool = False
    extracciones: bool = False
    extracciones_texto: str | None = Field(default=None, max_length=300)
    complicaciones_operatorias: bool = False
    complicaciones_operatorias_texto: str | None = Field(default=None, max_length=300)
    traumatismo_dental: bool = False
    traumatismo_dental_texto: str | None = Field(default=None, max_length=300)
    infecciones_dentales: bool = False
    infecciones_dentales_texto: str | None = Field(default=None, max_length=300)
    estres: bool = False
    estres_texto: str | None = Field(default=None, max_length=300)
    hospitalizacion_emergencia: bool = False
    hospitalizacion_emergencia_texto: str | None = Field(default=None, max_length=300)
    infecciones_frecuentes: bool = False
    infecciones_frecuentes_zona: str | None = Field(default=None, max_length=200)
    tiempo_evolucion: str | None = Field(default=None, max_length=200)
    # {codigo: {"present": bool, "evolution": str|None}}, codigo validado contra
    # el catalogo administrable "pathological_condition".
    diseases: dict[str, dict[str, object]] = Field(default_factory=dict)


class PersonalPathologicalHistoryOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    dolor_masticar: bool
    sensibilidad_frio: bool
    sensibilidad_calor: bool
    sensibilidad_dulce: bool
    sensibilidad_localizacion: str | None
    sangrado_encias: BleedingGumsLevel
    dolor_cepillado: bool
    aftas_ulceras: bool
    perdida_piezas: bool
    perdida_piezas_causa: str | None
    anestesia_previa: bool
    extracciones: bool
    extracciones_texto: str | None
    complicaciones_operatorias: bool
    complicaciones_operatorias_texto: str | None
    traumatismo_dental: bool
    traumatismo_dental_texto: str | None
    infecciones_dentales: bool
    infecciones_dentales_texto: str | None
    estres: bool
    estres_texto: str | None
    hospitalizacion_emergencia: bool
    hospitalizacion_emergencia_texto: str | None
    infecciones_frecuentes: bool
    infecciones_frecuentes_zona: str | None
    tiempo_evolucion: str | None
    diseases: dict[str, dict[str, object]]
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


class PersonalNonPathologicalHistoryCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    comidas_dia: int | None = Field(default=None, ge=0, le=20)
    calidad_alimentacion: FoodQualityLevel | None = None
    agua_litros_dia: float | None = Field(default=None, ge=0, le=20)
    trastornos_sueno: bool = False
    trastornos_sueno_texto: str | None = Field(default=None, max_length=300)
    cepillados_dia: int | None = Field(default=None, ge=0, le=20)
    hilo_dental: bool = False
    enjuague_bucal: bool = False
    deportes: bool = False
    deportes_cual: str | None = Field(default=None, max_length=200)
    derechohabiencia: HealthCoverageType | None = None
    estado_civil: MaritalStatus | None = Field(default=None, max_length=60)
    medicamentos_suplementos: bool = False
    medicamentos_controlados: bool = False
    medicamentos_texto: str | None = Field(default=None, max_length=300)
    # {servicio: {"has": bool, "notes": str|None}}
    servicios_basicos: dict[str, dict[str, object]] = Field(default_factory=dict)
    # {sustancia: {"has": bool, "detail": str|None, "fecha_inicio": str|None}}
    adicciones: dict[str, dict[str, object]] = Field(default_factory=dict)


class PersonalNonPathologicalHistoryOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    comidas_dia: int | None
    calidad_alimentacion: FoodQualityLevel | None
    agua_litros_dia: float | None
    trastornos_sueno: bool
    trastornos_sueno_texto: str | None
    cepillados_dia: int | None
    hilo_dental: bool
    enjuague_bucal: bool
    deportes: bool
    deportes_cual: str | None
    derechohabiencia: HealthCoverageType | None
    estado_civil: MaritalStatus | None
    medicamentos_suplementos: bool
    medicamentos_controlados: bool
    medicamentos_texto: str | None
    servicios_basicos: dict[str, dict[str, object]]
    adicciones: dict[str, dict[str, object]]
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


class SystemsReviewEntryCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    # Para los 6 aparatos/sistemas con catalogo administrable
    # ("systems_review_finding"): {codigo: {"present": bool, "evolution": str|None}}.
    hematologico: dict[str, dict[str, object]] = Field(default_factory=dict)
    cardiovascular: dict[str, dict[str, object]] = Field(default_factory=dict)
    neurologico: dict[str, dict[str, object]] = Field(default_factory=dict)
    endocrino: dict[str, dict[str, object]] = Field(default_factory=dict)
    respiratorio: dict[str, dict[str, object]] = Field(default_factory=dict)
    genitourinario: dict[str, dict[str, object]] = Field(default_factory=dict)
    # Reproductor masculino/femenino: campos propios (inicio de vida sexual,
    # embarazos, partos, metodos anticonceptivos, etc.), forma libre -- no se
    # valida contra catalogo (mezclan booleanos, fechas y conteos).
    reproductor_masculino: dict[str, object] = Field(default_factory=dict)
    reproductor_femenino: dict[str, object] = Field(default_factory=dict)


class SystemsReviewEntryOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    hematologico: dict[str, dict[str, object]]
    cardiovascular: dict[str, dict[str, object]]
    neurologico: dict[str, dict[str, object]]
    endocrino: dict[str, dict[str, object]]
    respiratorio: dict[str, dict[str, object]]
    genitourinario: dict[str, dict[str, object]]
    reproductor_masculino: dict[str, object]
    reproductor_femenino: dict[str, object]
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


def _validate_catalogs() -> None:
    assert set(SEVERITY_LEVELS) == set(Severity.__args__)  # type: ignore[attr-defined]
    assert set(ORIGINS) == set(Origin.__args__)  # type: ignore[attr-defined]
    assert set(GLUCOSE_TIMINGS) == set(GlucoseTiming.__args__)  # type: ignore[attr-defined]
    assert set(PATIENT_ATTITUDES) == set(PatientAttitude.__args__)  # type: ignore[attr-defined]
    assert set(FAMILY_STATUSES) == set(FamilyStatus.__args__)  # type: ignore[attr-defined]
    assert set(BLEEDING_GUMS_LEVELS) == set(BleedingGumsLevel.__args__)  # type: ignore[attr-defined]
    assert set(FOOD_QUALITY_LEVELS) == set(FoodQualityLevel.__args__)  # type: ignore[attr-defined]
    assert set(HEALTH_COVERAGE_TYPES) == set(HealthCoverageType.__args__)  # type: ignore[attr-defined]
    # MaritalStatus ya no es un Literal cerrado (correccion Fase A: el formulario
    # ofrece MARITAL_STATUSES como sugerencias mas "Otro" con texto libre), asi
    # que no hay un conjunto fijo de valores que validar aqui.


_validate_catalogs()
