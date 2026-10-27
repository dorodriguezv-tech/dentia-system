import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.endodontic_history.rules import (
    DIAGNOSTICO_PERIAPICAL_VALUES,
    DIAGNOSTICO_PULPAR_VALUES,
    ENDODONTIC_TOOTH_KINDS,
    MOVILIDAD_GRADOS,
    MOVILIDAD_VALUES,
    ORIGINS,
    PALPACION_VALUES,
)

Origin = Literal["MANUAL", "AI_ASSISTED"]
MovilidadValue = Literal["positiva", "negativa"]
MovilidadGrado = Literal["I", "II", "III"]
PalpacionValue = Literal["positiva", "negativa"]
DiagnosticoPulpar = Literal[
    "pulpa_sana",
    "pulpitis_reversible",
    "pulpitis_irreversible",
    "necrosis_pulpar",
    "despulpado",
    "pulpitis_hiperplasica",
]
DiagnosticoPeriapical = Literal[
    "periapice_sano",
    "periodontitis_aguda",
    "periodontitis_cronica",
    "osteitis_condensante",
    "absceso_alveolar_agudo",
    "absceso_fenix_cronico",
]
EndodonticToothKind = Literal["diagnostico", "evolucion"]


class AnnulRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


# --------------------------------------------------------------------------------
# 1. Interrogatorio + examen intrabucal/extrabucal.
# --------------------------------------------------------------------------------


class EndodonticInterrogationCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    antecedentes: dict[str, bool] = Field(default_factory=dict)
    antecedentes_otro_detalle: str | None = Field(default=None, max_length=500)
    dolor: dict[str, bool] = Field(default_factory=dict)
    dolor_otro_detalle: str | None = Field(default=None, max_length=500)
    estimulo: dict[str, bool] = Field(default_factory=dict)
    estimulo_otro_detalle: str | None = Field(default=None, max_length=500)
    examen_intrabucal: dict[str, bool] = Field(default_factory=dict)
    examen_intrabucal_otro_detalle: str | None = Field(default=None, max_length=500)
    examen_extrabucal: dict[str, bool] = Field(default_factory=dict)
    examen_extrabucal_otro_detalle: str | None = Field(default=None, max_length=500)


class EndodonticInterrogationOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    antecedentes: dict[str, bool]
    antecedentes_otro_detalle: str | None
    dolor: dict[str, bool]
    dolor_otro_detalle: str | None
    estimulo: dict[str, bool]
    estimulo_otro_detalle: str | None
    examen_intrabucal: dict[str, bool]
    examen_intrabucal_otro_detalle: str | None
    examen_extrabucal: dict[str, bool]
    examen_extrabucal_otro_detalle: str | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 2. Pruebas de sensibilidad pulpar.
# --------------------------------------------------------------------------------


class EndodonticPulpSensitivityTestCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    frio: bool = False
    calor: bool = False
    fugaz: bool = False
    persistente: bool = False
    localizado: bool = False
    irradiado: bool = False
    decrece: bool = False
    incrementa: bool = False
    diente_testigo_od: str | None = Field(default=None, max_length=50)
    prueba_cavidad: str | None = Field(default=None, max_length=200)
    prueba_electrica_od: str | None = Field(default=None, max_length=50)


class EndodonticPulpSensitivityTestOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    frio: bool
    calor: bool
    fugaz: bool
    persistente: bool
    localizado: bool
    irradiado: bool
    decrece: bool
    incrementa: bool
    diente_testigo_od: str | None
    prueba_cavidad: str | None
    prueba_electrica_od: str | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 3. Pruebas periodontales.
# --------------------------------------------------------------------------------


class EndodonticPeriodontalTestCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    percusion_horizontal: dict[str, bool] = Field(default_factory=dict)
    movilidad_horizontal: MovilidadValue | None = None
    movilidad_horizontal_grado: MovilidadGrado | None = None
    percusion_vertical: dict[str, bool] = Field(default_factory=dict)
    movilidad_vertical: MovilidadValue | None = None
    movilidad_vertical_grado: MovilidadGrado | None = None
    palpacion: PalpacionValue | None = None


class EndodonticPeriodontalTestOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    percusion_horizontal: dict[str, bool]
    movilidad_horizontal: MovilidadValue | None
    movilidad_horizontal_grado: MovilidadGrado | None
    percusion_vertical: dict[str, bool]
    movilidad_vertical: MovilidadValue | None
    movilidad_vertical_grado: MovilidadGrado | None
    palpacion: PalpacionValue | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 4. Interpretacion radiografica.
# --------------------------------------------------------------------------------


class EndodonticRadiographicInterpretationCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    camara: dict[str, bool] = Field(default_factory=dict)
    camara_otro_detalle: str | None = Field(default=None, max_length=500)
    conducto: dict[str, bool] = Field(default_factory=dict)
    conducto_otro_detalle: str | None = Field(default=None, max_length=500)
    periodonto: dict[str, bool] = Field(default_factory=dict)
    periodonto_otro_detalle: str | None = Field(default=None, max_length=500)


class EndodonticRadiographicInterpretationOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    camara: dict[str, bool]
    camara_otro_detalle: str | None
    conducto: dict[str, bool]
    conducto_otro_detalle: str | None
    periodonto: dict[str, bool]
    periodonto_otro_detalle: str | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 5. Diagnostico y tratamiento.
# --------------------------------------------------------------------------------


class EndodonticDiagnosisTreatmentCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    diagnostico_pulpar: DiagnosticoPulpar | None = None
    diagnostico_periapical: DiagnosticoPeriapical | None = None
    tratamiento: dict[str, bool] = Field(default_factory=dict)
    cirugia: dict[str, bool] = Field(default_factory=dict)


class EndodonticDiagnosisTreatmentOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    diagnostico_pulpar: DiagnosticoPulpar | None
    diagnostico_periapical: DiagnosticoPeriapical | None
    tratamiento: dict[str, bool]
    cirugia: dict[str, bool]
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 6. Odontograma de diagnostico/evolucion -- 18 codigos por pieza.
# --------------------------------------------------------------------------------


class EndodonticToothDiagnosisCodeCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    tooth_fdi: str = Field(min_length=2, max_length=2)
    kind: EndodonticToothKind
    code: int = Field(ge=0, le=17)


class EndodonticToothDiagnosisCodeOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    tooth_fdi: str
    kind: EndodonticToothKind
    code: int
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


# --------------------------------------------------------------------------------
# 7. Longitud de trabajo + datos de tratamiento.
# --------------------------------------------------------------------------------


class CanalMeasurementDetail(BaseModel):
    aparente_rx: str | None = Field(default=None, max_length=50)
    real_localizador: str | None = Field(default=None, max_length=50)
    relacion: str | None = Field(default=None, max_length=50)


class EndodonticWorkingLengthCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    tooth_fdi: str | None = Field(default=None, min_length=2, max_length=2)
    # {clave_conducto: {...}}, clave_conducto una de rules.CANAL_KEYS.
    canal_measurements: dict[str, CanalMeasurementDetail] = Field(default_factory=dict)
    tecnica_instrumentacion: str | None = Field(default=None, max_length=500)
    tecnica_obturacion: str | None = Field(default=None, max_length=500)
    indicaciones: str | None = Field(default=None, max_length=1000)
    fecha_inicio: str | None = Field(default=None, max_length=100)
    fecha_termino: str | None = Field(default=None, max_length=100)


class EndodonticWorkingLengthOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    tooth_fdi: str | None
    canal_measurements: dict[str, CanalMeasurementDetail]
    tecnica_instrumentacion: str | None
    tecnica_obturacion: str | None
    indicaciones: str | None
    fecha_inicio: str | None
    fecha_termino: str | None
    is_active: bool
    origin: Origin
    created_at: datetime

    model_config = {"from_attributes": True}


def _validate_catalogs() -> None:
    assert set(ORIGINS) == set(Origin.__args__)  # type: ignore[attr-defined]
    assert set(MOVILIDAD_VALUES) == set(MovilidadValue.__args__)  # type: ignore[attr-defined]
    assert set(MOVILIDAD_GRADOS) == set(MovilidadGrado.__args__)  # type: ignore[attr-defined]
    assert set(PALPACION_VALUES) == set(PalpacionValue.__args__)  # type: ignore[attr-defined]
    assert set(DIAGNOSTICO_PULPAR_VALUES) == set(
        DiagnosticoPulpar.__args__  # type: ignore[attr-defined]
    )
    assert set(DIAGNOSTICO_PERIAPICAL_VALUES) == set(
        DiagnosticoPeriapical.__args__  # type: ignore[attr-defined]
    )
    assert set(ENDODONTIC_TOOTH_KINDS) == set(
        EndodonticToothKind.__args__  # type: ignore[attr-defined]
    )


_validate_catalogs()
