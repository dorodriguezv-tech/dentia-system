import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.documents.rules import SIGNER_RELATIONSHIPS, TEMPLATE_CODES

TemplateCode = Literal[
    "protesis_fija",
    "aplicacion_fluor",
    "anestesia_local_oral",
    "exodoncia",
    "incrustacion_dental",
    "obturacion_dental",
    "endodoncia",
    "protesis_removible",
    "sellado_fosetas_fisuras",
    "toma_radiografias",
    "limpieza_dental",
    "aplicacion_fluor_pediatrico",
    "anestesia_local_pediatrico",
    "corona_metalica_pediatrico",
    "sellado_fosetas_pediatrico",
    "obturacion_resina_pediatrico",
    "profilaxis_pediatrico",
    "toma_radiografias_pediatrico",
    "tratamiento_pulpar_pediatrico",
    "aviso_privacidad",
    "carta_tratamiento_concluido",
    "carta_tratamiento_suspendido",
    "carta_autorizacion_uso_imagen",
    "carta_caso_medico_legal",
]
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
    # Datos libres que el formato elegido pide (rules.TEMPLATE_EXTRA_FIELDS) --
    # vacio para la mayoria de formatos, que no piden nada mas.
    extra_fields: dict[str, str] = Field(default_factory=dict)
    witness1_name: str | None = Field(default=None, max_length=200)
    witness2_name: str | None = Field(default=None, max_length=200)

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
    extra_fields: dict[str, str] | None
    witness1_name: str | None
    witness2_name: str | None
    content_hash: str
    signed_at: datetime
    is_active: bool
    annul_reason: str | None

    model_config = {"from_attributes": True}


class ExtraFieldPrefill(BaseModel):
    label: str
    required: bool
    multiline: bool
    value: str | None


class ConsentPrefillOut(BaseModel):
    """Lo que el frontend necesita para mostrar 'datos que se usaran' + 'falta
    completar' antes de firmar (ver documents/service.py::build_consent_prefill).
    `variables` es el mismo diccionario que create_consent arma internamente
    para render_template -- se expone aqui para no duplicar esa logica en
    TypeScript."""

    variables: dict[str, object]
    extra_fields: dict[str, ExtraFieldPrefill]


class AnnulRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


def _validate_catalogs() -> None:
    assert set(TEMPLATE_CODES) == set(TemplateCode.__args__)  # type: ignore[attr-defined]
    assert set(SIGNER_RELATIONSHIPS) == set(SignerRelationship.__args__)  # type: ignore[attr-defined]


_validate_catalogs()
