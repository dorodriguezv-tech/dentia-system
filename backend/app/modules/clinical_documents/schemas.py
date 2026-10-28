import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.clinical_documents.rules import MAX_MEDICATIONS_PER_PRESCRIPTION


class PrescriptionMedicationItem(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    # Forma farmaceutica, dosis, presentacion, frecuencia, via de administracion,
    # duracion del tratamiento e indicaciones: una sola celda de texto libre grande,
    # tal como lo muestra el formato oficial (docs/clinica/receta.pdf).
    detalle: str = Field(min_length=1, max_length=1000)


class PrescriptionCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    diagnostico: str = Field(min_length=1, max_length=2000)
    medications: list[PrescriptionMedicationItem] = Field(
        min_length=1, max_length=MAX_MEDICATIONS_PER_PRESCRIPTION
    )


class PrescriptionOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    encounter_id: uuid.UUID
    folio: str
    diagnostico: str
    medications: list[PrescriptionMedicationItem]
    is_active: bool
    annul_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReferralNoteCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    diagnosticos: str | None = Field(default=None, max_length=2000)
    medicamentos_texto: str | None = Field(default=None, max_length=2000)
    alergias_texto: str | None = Field(default=None, max_length=2000)
    tratamientos_texto: str | None = Field(default=None, max_length=2000)
    observaciones: str | None = Field(default=None, max_length=2000)
    motivo_interconsulta: str = Field(min_length=1, max_length=2000)
    establecimiento_receptor: str = Field(min_length=1, max_length=300)


class ReferralNoteOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    encounter_id: uuid.UUID
    diagnosticos: str | None
    medicamentos_texto: str | None
    alergias_texto: str | None
    tratamientos_texto: str | None
    observaciones: str | None
    motivo_interconsulta: str
    establecimiento_receptor: str
    is_active: bool
    annul_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CounterReferralNoteCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    referral_note_id: uuid.UUID | None = None
    motivo_contrarreferencia: str = Field(min_length=1, max_length=2000)
    tratamientos_texto: str | None = Field(default=None, max_length=2000)
    observaciones: str | None = Field(default=None, max_length=2000)
    motivo_interconsulta_original: str | None = Field(default=None, max_length=2000)
    establecimiento_emisor: str = Field(min_length=1, max_length=300)


class CounterReferralNoteOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    encounter_id: uuid.UUID
    referral_note_id: uuid.UUID | None
    motivo_contrarreferencia: str
    tratamientos_texto: str | None
    observaciones: str | None
    motivo_interconsulta_original: str | None
    establecimiento_emisor: str
    is_active: bool
    annul_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnnulRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
