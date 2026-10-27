import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.pediatric_history.rules import (
    CLASIFICACION_ANGLE_OPTIONS,
    LINEA_MEDIA_OPTIONS,
    ORIGINS,
)

Origin = Literal["MANUAL", "AI_ASSISTED"]
# Catalogos administrables (app.modules.catalogs): no son Literal fijo, se
# validan contra la BD en el service (igual que SkullType de Fase C).
PediatricCharacter = str
TerminalPlane = str
PediatricToothAnomaly = str
LineaMedia = Literal["normal", "desviada_izquierda", "desviada_derecha"]
ClasificacionAngle = Literal["I", "II", "III"]


class AnnulRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


# --------------------------------------------------------------------------------
# 1. Antecedentes perinatales y primer ano de vida.
# --------------------------------------------------------------------------------


class PediatricPerinatalHistoryCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    problemas_embarazo_perinatales: str | None = Field(default=None, max_length=2000)
    tomo_medicamentos_embarazo: bool | None = None
    tomo_medicamentos_embarazo_cuales: str | None = Field(default=None, max_length=500)
    embarazo_observaciones: str | None = Field(default=None, max_length=2000)
    tomo_medicamentos_primer_ano: bool | None = None
    tomo_medicamentos_primer_ano_cuales: str | None = Field(default=None, max_length=500)
    vacunas_completas: bool | None = None
    fecha_ultima_visita_dentista: str | None = Field(default=None, max_length=100)


class PediatricPerinatalHistoryOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    problemas_embarazo_perinatales: str | None
    tomo_medicamentos_embarazo: bool | None
    tomo_medicamentos_embarazo_cuales: str | None
    embarazo_observaciones: str | None
    tomo_medicamentos_primer_ano: bool | None
    tomo_medicamentos_primer_ano_cuales: str | None
    vacunas_completas: bool | None
    fecha_ultima_visita_dentista: str | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 2. Habitos y antecedentes bucales.
# --------------------------------------------------------------------------------


class PediatricOralHabitsCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    cepilla_despues_alimento: bool | None = None
    sangran_encias_sin_cepillar: bool | None = None
    sabe_que_es_fluor: bool | None = None
    fluoruro_sistematico_aplicado: bool | None = None
    diente_extraido: bool | None = None
    accidentes_fracturas_dentales: bool | None = None
    dolor_dental_reciente: bool | None = None
    bruxismo_nocturno: bool | None = None
    respira_boca_frecuente: bool | None = None


class PediatricOralHabitsOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    cepilla_despues_alimento: bool | None
    sangran_encias_sin_cepillar: bool | None
    sabe_que_es_fluor: bool | None
    fluoruro_sistematico_aplicado: bool | None
    diente_extraido: bool | None
    accidentes_fracturas_dentales: bool | None
    dolor_dental_reciente: bool | None
    bruxismo_nocturno: bool | None
    respira_boca_frecuente: bool | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 3. Madurez y conducta.
# --------------------------------------------------------------------------------


class PediatricBehaviorMaturityCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    experiencia_desfavorable_dentista: bool | None = None
    se_relaciona_medico: bool | None = None
    controla_esfinteres: bool | None = None
    toma_biberon_actualmente: bool | None = None
    edad_dejo_biberon: str | None = Field(default=None, max_length=100)
    succion_labio_dedo: bool | None = None
    muerde_objetos_unas: bool | None = None
    relacion_otros_ninos: str | None = Field(default=None, max_length=2000)
    caracter: PediatricCharacter | None = Field(default=None, max_length=40)
    observaciones: str | None = Field(default=None, max_length=2000)


class PediatricBehaviorMaturityOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    experiencia_desfavorable_dentista: bool | None
    se_relaciona_medico: bool | None
    controla_esfinteres: bool | None
    toma_biberon_actualmente: bool | None
    edad_dejo_biberon: str | None
    succion_labio_dedo: bool | None
    muerde_objetos_unas: bool | None
    relacion_otros_ninos: str | None
    caracter: PediatricCharacter | None
    observaciones: str | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 4. Oclusion y alineamiento.
# --------------------------------------------------------------------------------


class PediatricOcclusionCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    planos_terminales_izq: TerminalPlane | None = Field(default=None, max_length=40)
    planos_terminales_der: TerminalPlane | None = Field(default=None, max_length=40)
    angle_molar_izq: str | None = Field(default=None, max_length=200)
    angle_molar_der: str | None = Field(default=None, max_length=200)
    overjet_mm: float | None = Field(default=None, ge=0, le=30)
    overbite_mm: float | None = Field(default=None, ge=-10, le=30)
    mordida_cruzada: bool | None = None
    diastema: bool | None = None
    mordida_abierta_ante_mm: float | None = Field(default=None, ge=0, le=30)
    mordida_abierta_post_mm: float | None = Field(default=None, ge=0, le=30)
    linea_media: LineaMedia | None = None
    clasificacion_angle: ClasificacionAngle | None = None


class PediatricOcclusionOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    planos_terminales_izq: TerminalPlane | None
    planos_terminales_der: TerminalPlane | None
    angle_molar_izq: str | None
    angle_molar_der: str | None
    overjet_mm: float | None
    overbite_mm: float | None
    mordida_cruzada: bool | None
    diastema: bool | None
    mordida_abierta_ante_mm: float | None
    mordida_abierta_post_mm: float | None
    linea_media: LineaMedia | None
    clasificacion_angle: ClasificacionAngle | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 5. Erupcion y denticion.
# --------------------------------------------------------------------------------


class PediatricEruptionDentitionCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    secuencia_normal: bool | None = None
    perdida_prematura: bool | None = None
    retencion_prolongada: bool | None = None
    erupcion_retardada: bool | None = None
    falta_contacto_proximal: bool | None = None
    malposicion_dentaria: bool | None = None
    otras_anormalidades: str | None = Field(default=None, max_length=2000)
    edad_dental: str | None = Field(default=None, max_length=100)
    estado_general_higiene: str | None = Field(default=None, max_length=2000)


class PediatricEruptionDentitionOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    secuencia_normal: bool | None
    perdida_prematura: bool | None
    retencion_prolongada: bool | None
    erupcion_retardada: bool | None
    falta_contacto_proximal: bool | None
    malposicion_dentaria: bool | None
    otras_anormalidades: str | None
    edad_dental: str | None
    estado_general_higiene: str | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 6. Odontograma pediatrico -- anotaciones por pieza.
# --------------------------------------------------------------------------------


class PediatricToothAnnotationCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    tooth_fdi: str = Field(min_length=2, max_length=2)
    anomaly_code: PediatricToothAnomaly = Field(max_length=40)
    hipoplasia_detail: str | None = Field(default=None, max_length=300)


class PediatricToothAnnotationOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    tooth_fdi: str
    anomaly_code: PediatricToothAnomaly
    hipoplasia_detail: str | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


def _validate_catalogs() -> None:
    assert set(ORIGINS) == set(Origin.__args__)  # type: ignore[attr-defined]
    assert set(LINEA_MEDIA_OPTIONS) == set(LineaMedia.__args__)  # type: ignore[attr-defined]
    assert set(CLASIFICACION_ANGLE_OPTIONS) == set(
        ClasificacionAngle.__args__  # type: ignore[attr-defined]
    )


_validate_catalogs()
