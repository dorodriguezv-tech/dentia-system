import base64
import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import AppError
from app.core.storage import StorageBackend
from app.modules.branding import service as branding_service
from app.modules.documents.models import Consent, DocumentTemplate
from app.modules.documents.pdf import PdfRenderError, build_consent_pdf
from app.modules.documents.rules import SIGNER_RELATIONSHIPS
from app.modules.documents.schemas import (
    AnnulRequest,
    ConsentCreateRequest,
    DocumentTemplateCreateRequest,
)
from app.modules.encounters.models import Encounter
from app.modules.iam.models import User
from app.modules.patients.models import Patient
from app.modules.treatment.models import ProcedurePlanned, TreatmentPlan

_SIGNER_RELATIONSHIP_LABELS = {"paciente": "Paciente", "tutor": "Tutor", "otro": "Otro"}

MAX_SIGNATURE_BYTES = 500_000


async def _get_patient_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> Patient:
    patient = await db.get(Patient, patient_id)
    if patient is None or patient.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Paciente no encontrado", status_code=404)
    return patient


async def _get_encounter_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, encounter_id: uuid.UUID
) -> Encounter:
    encounter = await db.get(Encounter, encounter_id)
    if encounter is None or encounter.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Atencion no encontrada", status_code=404)
    return encounter


# --------------------------------------------------------------------------- plantillas


async def list_templates(db: AsyncSession, *, clinic_id: uuid.UUID) -> list[DocumentTemplate]:
    stmt = select(DocumentTemplate).where(
        DocumentTemplate.clinic_id == clinic_id, DocumentTemplate.is_current.is_(True)
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_template_history(
    db: AsyncSession, *, clinic_id: uuid.UUID, code: str
) -> list[DocumentTemplate]:
    stmt = (
        select(DocumentTemplate)
        .where(DocumentTemplate.clinic_id == clinic_id, DocumentTemplate.code == code)
        .order_by(DocumentTemplate.version.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def _get_current_template(
    db: AsyncSession, *, clinic_id: uuid.UUID, code: str
) -> DocumentTemplate:
    stmt = select(DocumentTemplate).where(
        DocumentTemplate.clinic_id == clinic_id,
        DocumentTemplate.code == code,
        DocumentTemplate.is_current.is_(True),
    )
    template = (await db.execute(stmt)).scalar_one_or_none()
    if template is None:
        raise AppError(
            "NOT_FOUND",
            f"No hay una plantilla configurada para '{code}' en esta clinica",
            status_code=404,
        )
    return template


async def create_template_version(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    data: DocumentTemplateCreateRequest,
    actor_id: uuid.UUID,
) -> DocumentTemplate:
    previous = await db.execute(
        select(DocumentTemplate)
        .where(DocumentTemplate.clinic_id == clinic_id, DocumentTemplate.code == data.code)
        .order_by(DocumentTemplate.version.desc())
        .limit(1)
    )
    previous_version = previous.scalar_one_or_none()
    if previous_version is not None:
        previous_version.is_current = False

    template = DocumentTemplate(
        clinic_id=clinic_id,
        code=data.code,
        name=data.name,
        version=(previous_version.version + 1) if previous_version else 1,
        html_content=data.html_content,
        supersedes_id=previous_version.id if previous_version else None,
        is_current=True,
        created_by=actor_id,
    )
    db.add(template)
    await db.flush()

    await audit_service.log(
        db,
        action="documents.template_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="document_template",
        entity_id=str(template.id),
        details={"code": data.code, "version": template.version},
    )
    await db.commit()
    return template


# ----------------------------------------------------------------------- consentimientos


def _decode_signature(raw: str) -> bytes:
    if raw.startswith("data:"):
        _, _, raw = raw.partition(",")
    try:
        data = base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise AppError(
            "INVALID_SIGNATURE", "La firma no es un PNG valido", status_code=400
        ) from exc
    if len(data) > MAX_SIGNATURE_BYTES:
        raise AppError("FILE_TOO_LARGE", "La firma no puede pesar mas de 500 KB", status_code=400)
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AppError("INVALID_SIGNATURE", "La firma debe ser una imagen PNG", status_code=400)
    return data


async def create_consent(
    db: AsyncSession,
    storage: StorageBackend,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: ConsentCreateRequest,
    actor: User,
) -> Consent:
    patient = await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    encounter = await _get_encounter_in_clinic(
        db, clinic_id=clinic_id, encounter_id=data.encounter_id
    )
    if encounter.patient_id != patient_id:
        raise AppError(
            "ENCOUNTER_PATIENT_MISMATCH",
            "La atencion no pertenece a este paciente",
            status_code=400,
        )
    template = await _get_current_template(db, clinic_id=clinic_id, code=data.template_code)

    procedure_name = None
    if data.procedure_planned_id is not None:
        planned = await db.get(ProcedurePlanned, data.procedure_planned_id)
        if planned is None or planned.clinic_id != clinic_id or planned.patient_id != patient_id:
            raise AppError("NOT_FOUND", "Procedimiento planificado no encontrado", status_code=404)
        procedure_name = planned.procedure_name

    plan_title = None
    if data.treatment_plan_id is not None:
        plan = await db.get(TreatmentPlan, data.treatment_plan_id)
        if plan is None or plan.clinic_id != clinic_id or plan.patient_id != patient_id:
            raise AppError("NOT_FOUND", "Plan de tratamiento no encontrado", status_code=404)
        plan_title = plan.title

    signature_bytes = _decode_signature(data.signature_png_base64)

    signed_at = datetime.now(UTC)
    branding = await branding_service.get_branding(db)
    logo = await branding_service.read_logo(db, storage)

    age_years = (signed_at.date() - patient.date_of_birth).days // 365
    variables = {
        "paciente": {"nombre": patient.full_name, "edad": age_years},
        "procedimiento": {"nombre": procedure_name} if procedure_name else "",
        "plan": {"titulo": plan_title} if plan_title else "",
        "clinica": {"nombre": branding.display_name},
        "fecha": signed_at.strftime("%d/%m/%Y %H:%M"),
        "profesional": {"nombre": actor.full_name, "cedula": actor.professional_license or ""},
    }

    try:
        pdf_bytes = build_consent_pdf(
            template_name=template.name,
            html_content=template.html_content,
            variables=variables,
            signature_png=signature_bytes,
            clinic_name=branding.display_name,
            patient_name=patient.full_name,
            signer_name=data.signer_name,
            signer_relationship_label=_SIGNER_RELATIONSHIP_LABELS[data.signer_relationship],
            signed_at_label=signed_at.strftime("%d/%m/%Y %H:%M"),
            logo=logo,
        )
    except PdfRenderError as exc:
        raise AppError("PDF_RENDER_ERROR", str(exc), status_code=500) from exc

    content_hash = hashlib.sha256(pdf_bytes).hexdigest()
    signature_path = storage.save(
        signature_bytes, subdir=f"documents/{clinic_id}/{patient_id}", suffix=".png"
    )
    pdf_path = storage.save(pdf_bytes, subdir=f"documents/{clinic_id}/{patient_id}", suffix=".pdf")

    consent = Consent(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        template_id=template.id,
        procedure_planned_id=data.procedure_planned_id,
        treatment_plan_id=data.treatment_plan_id,
        professional_id=actor.id,
        signer_name=data.signer_name,
        signer_relationship=data.signer_relationship,
        signature_path=signature_path,
        pdf_path=pdf_path,
        content_hash=content_hash,
        signed_at=signed_at,
        created_by=actor.id,
    )
    db.add(consent)
    await db.flush()

    await audit_service.log(
        db,
        action="documents.consent_signed",
        actor_user_id=actor.id,
        clinic_id=clinic_id,
        entity_type="consent",
        entity_id=str(consent.id),
        details={
            "patient_id": str(patient_id),
            "template_code": data.template_code,
            "content_hash": content_hash,
        },
    )
    await db.commit()
    return consent


async def list_consents(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[Consent]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(Consent)
        .where(Consent.clinic_id == clinic_id, Consent.patient_id == patient_id)
        .order_by(Consent.signed_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def _get_consent_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, consent_id: uuid.UUID
) -> Consent:
    consent = await db.get(Consent, consent_id)
    if consent is None or consent.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Consentimiento no encontrado", status_code=404)
    return consent


async def get_consent_pdf(
    db: AsyncSession,
    storage: StorageBackend,
    *,
    clinic_id: uuid.UUID,
    consent_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> bytes:
    consent = await _get_consent_in_clinic(db, clinic_id=clinic_id, consent_id=consent_id)
    await audit_service.log(
        db,
        action="documents.consent_read",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="consent",
        entity_id=str(consent.id),
    )
    await db.commit()
    return storage.read(consent.pdf_path)


async def annul_consent(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    consent_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> Consent:
    consent = await _get_consent_in_clinic(db, clinic_id=clinic_id, consent_id=consent_id)
    consent.is_active = False
    consent.annul_reason = data.reason
    consent.annulled_by = actor_id
    consent.annulled_at = datetime.now(UTC)

    await audit_service.log(
        db,
        action="documents.consent_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="consent",
        entity_id=str(consent_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return consent


def _validate_catalogs() -> None:
    assert set(SIGNER_RELATIONSHIPS) == set(_SIGNER_RELATIONSHIP_LABELS.keys())


_validate_catalogs()
