import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

NoteStatus = Literal["DRAFT", "FINAL", "CORRECTED", "CANCELLED"]


class EncounterCreateRequest(BaseModel):
    patient_id: uuid.UUID
    chief_complaint: str | None = Field(default=None, max_length=2000)
    appointment_id: uuid.UUID | None = None


class EncounterOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    professional_id: uuid.UUID
    appointment_id: uuid.UUID | None
    chief_complaint: str | None
    started_at: datetime
    ended_at: datetime | None

    model_config = {"from_attributes": True}


class ClinicalNoteCreateRequest(BaseModel):
    soap_s: str | None = None
    soap_o: str | None = None
    soap_a: str | None = None
    soap_p: str | None = None
    free_text: str | None = None


class ClinicalNoteUpdateRequest(BaseModel):
    soap_s: str | None = None
    soap_o: str | None = None
    soap_a: str | None = None
    soap_p: str | None = None
    free_text: str | None = None


class ClinicalNoteOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    patient_id: uuid.UUID
    author_id: uuid.UUID
    status: NoteStatus
    soap_s: str | None
    soap_o: str | None
    soap_a: str | None
    soap_p: str | None
    free_text: str | None
    version: int
    previous_version_id: uuid.UUID | None
    correction_reason: str | None
    content_hash: str | None
    finalized_at: datetime | None
    cancel_reason: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class FinalizeNoteRequest(BaseModel):
    """alerts_acknowledged: el frontend debe mostrar el modal de alertas criticas
    (regla 8 de CLAUDE.md) antes de mandar true; si el paciente tiene alertas activas
    y no se confirma, el backend rechaza la finalizacion."""

    alerts_acknowledged: bool = False


class CorrectNoteRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class CancelNoteRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class TimelineNoteOut(BaseModel):
    id: uuid.UUID
    status: NoteStatus
    version: int
    finalized_at: datetime | None


class CurrentEncounterOut(BaseModel):
    """B10 (docs/06_APP_MOVIL_V1_1_PARIDAD.md sec. 4): la atencion que el profesional
    dejo abierta, para la barra "En consulta" del movil y recuperarla al reabrir la
    app."""

    id: uuid.UUID
    patient_id: uuid.UUID
    patient_full_name: str
    started_at: datetime
    chief_complaint: str | None


class TimelineEntryOut(BaseModel):
    encounter_id: uuid.UUID
    started_at: datetime
    chief_complaint: str | None
    professional_name: str
    notes: list[TimelineNoteOut]
