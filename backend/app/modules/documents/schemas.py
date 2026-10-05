import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.documents.rules import SIGNER_RELATIONSHIPS, TEMPLATE_CODES

TemplateCode = Literal["general", "extraccion", "endodoncia", "anestesia"]
SignerRelationship = Literal["paciente", "tutor", "otro"]


class DocumentTemplateCreateRequest(BaseModel):
    code: TemplateCode
    name: str = Field(min_length=1, max_length=200)
    html_content: str = Field(min_length=1, max_length=50_000)


class DocumentTemplateOut(BaseModel):
    id: uuid.UUID
    code: TemplateCode
    name: str
    version: int
    html_content: str
    is_current: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ConsentCreateRequest(BaseModel):
    encounter_id: uuid.UUID
    template_code: TemplateCode
    procedure_planned_id: uuid.UUID | None = None
    treatment_plan_id: uuid.UUID | None = None
    signer_name: str = Field(min_length=1, max_length=200)
    signer_relationship: SignerRelationship = "paciente"
    # PNG de la firma capturada en el <canvas> del frontend, como data URL
    # ("data:image/png;base64,...") o solo el base64 sin el prefijo.
    signature_png_base64: str = Field(min_length=1)

    @model_validator(mode="after")
    def _at_most_one_link(self) -> "ConsentCreateRequest":
        if self.procedure_planned_id is not None and self.treatment_plan_id is not None:
            raise ValueError("Un consentimiento se liga a un procedimiento o a un plan, no a ambos")
        return self


class ConsentOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    encounter_id: uuid.UUID
    template_id: uuid.UUID
    procedure_planned_id: uuid.UUID | None
    treatment_plan_id: uuid.UUID | None
    professional_id: uuid.UUID
    signer_name: str
    signer_relationship: SignerRelationship
    content_hash: str
    signed_at: datetime
    is_active: bool
    annul_reason: str | None

    model_config = {"from_attributes": True}


class AnnulRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


def _validate_catalogs() -> None:
    assert set(TEMPLATE_CODES) == set(TemplateCode.__args__)  # type: ignore[attr-defined]
    assert set(SIGNER_RELATIONSHIPS) == set(SignerRelationship.__args__)  # type: ignore[attr-defined]


_validate_catalogs()
