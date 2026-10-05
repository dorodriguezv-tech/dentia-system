"""Acciones que la IA puede proponer (docs/03_AGENTE_IA_VOZ.md sec. 4): union discriminada
por "type". Son la salida esperada de Ollama (ver interpreter.py) y el contenido de
`AiSuggestion.payload` una vez validada. Ninguna accion aqui permite finalizar o firmar
notas, borrar, recetar, cobrar o cambiar datos de identidad (regla 9 de CLAUDE.md):
eso no es un campo que se pueda "apagar", simplemente no existe una accion para ello.
"""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.modules.diagnosis.schemas import DiagnosisCode
from app.modules.odontogram.schemas import FindingCode, Surface
from app.modules.records.schemas import HistoryCategory, Severity


class SetChiefComplaintAction(BaseModel):
    type: Literal["set_chief_complaint"] = "set_chief_complaint"
    text: str = Field(min_length=1, max_length=2000)


class AddAllergyAction(BaseModel):
    type: Literal["add_allergy"] = "add_allergy"
    substance: str = Field(min_length=1, max_length=200)
    reaction: str | None = Field(default=None, max_length=300)
    severity: Severity = "leve"


class AddMedicationAction(BaseModel):
    type: Literal["add_medication"] = "add_medication"
    name: str = Field(min_length=1, max_length=200)
    dose: str | None = Field(default=None, max_length=100)
    frequency: str | None = Field(default=None, max_length=100)


class AddMedicalHistoryAction(BaseModel):
    type: Literal["add_medical_history"] = "add_medical_history"
    category: HistoryCategory
    text: str = Field(min_length=1, max_length=2000)


class AddVitalSignsAction(BaseModel):
    type: Literal["add_vital_signs"] = "add_vital_signs"
    bp_sys: int | None = Field(default=None, ge=40, le=260)
    bp_dia: int | None = Field(default=None, ge=20, le=200)
    hr: int | None = Field(default=None, ge=20, le=250)
    temp: float | None = Field(default=None, ge=30, le=43)

    @model_validator(mode="after")
    def _at_least_one_value(self) -> Self:
        # Con todos los campos opcionales, un objeto vacio es "gratis" para la gramatica
        # del esquema: visto en pruebas reales, un modelo local de 7B bajo decodificacion
        # forzada lo usa como salida de minimo esfuerzo y la repite en vez de generar una
        # accion real. Exigir al menos un valor cierra ese atajo.
        if self.bp_sys is None and self.bp_dia is None and self.hr is None and self.temp is None:
            raise ValueError("add_vital_signs necesita al menos un valor")
        return self


class AddToothFindingAction(BaseModel):
    type: Literal["add_tooth_finding"] = "add_tooth_finding"
    tooth_fdi: int
    surfaces: list[Surface] = Field(default_factory=list)
    finding_code: FindingCode
    material: str | None = Field(default=None, max_length=100)


class AddPlannedProcedureAction(BaseModel):
    type: Literal["add_planned_procedure"] = "add_planned_procedure"
    tooth_fdi: int | None = None
    surfaces: list[Surface] = Field(default_factory=list)
    procedure_code: str = Field(min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=500)


class AddPerformedProcedureAction(BaseModel):
    type: Literal["add_performed_procedure"] = "add_performed_procedure"
    tooth_fdi: int | None = None
    surfaces: list[Surface] = Field(default_factory=list)
    procedure_code: str = Field(min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=500)


class AddDiagnosisAction(BaseModel):
    type: Literal["add_diagnosis"] = "add_diagnosis"
    text: str = Field(min_length=1, max_length=2000)
    diagnosis_code: DiagnosisCode | None = None
    tooth_fdi: int | None = None


class AppendNoteAction(BaseModel):
    type: Literal["append_note"] = "append_note"
    section: Literal["S", "O", "A", "P", "free"]
    text: str = Field(min_length=1, max_length=2000)


class ScheduleFollowupAction(BaseModel):
    type: Literal["schedule_followup"] = "schedule_followup"
    in_days: int = Field(ge=0, le=365)
    reason: str = Field(min_length=1, max_length=300)


AiAction = Annotated[
    SetChiefComplaintAction
    | AddAllergyAction
    | AddMedicationAction
    | AddMedicalHistoryAction
    | AddVitalSignsAction
    | AddToothFindingAction
    | AddPlannedProcedureAction
    | AddPerformedProcedureAction
    | AddDiagnosisAction
    | AppendNoteAction
    | ScheduleFollowupAction,
    Field(discriminator="type"),
]

ACTION_MODELS_BY_TYPE: dict[str, type[BaseModel]] = {
    "set_chief_complaint": SetChiefComplaintAction,
    "add_allergy": AddAllergyAction,
    "add_medication": AddMedicationAction,
    "add_medical_history": AddMedicalHistoryAction,
    "add_vital_signs": AddVitalSignsAction,
    "add_tooth_finding": AddToothFindingAction,
    "add_planned_procedure": AddPlannedProcedureAction,
    "add_performed_procedure": AddPerformedProcedureAction,
    "add_diagnosis": AddDiagnosisAction,
    "append_note": AppendNoteAction,
    "schedule_followup": ScheduleFollowupAction,
}


class UnrecognizedItem(BaseModel):
    text: str
    reason: str


class AiInterpretResult(BaseModel):
    """Esquema JSON que se le pide a Ollama (format=... en /api/chat, ver ollama_client.py)."""

    actions: list[AiAction] = Field(default_factory=list)
    unrecognized: list[UnrecognizedItem] = Field(default_factory=list)
