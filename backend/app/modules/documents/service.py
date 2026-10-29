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
from app.modules.documents.default_templates import DEFAULT_TEMPLATES
from app.modules.documents.models import Consent, DocumentTemplate
from app.modules.documents.pdf import PdfRenderError, build_consent_pdf
from app.modules.documents.pdf_header import get_pdf_header_info
from app.modules.documents.rules import (
    LEGACY_EXAMPLE_TEMPLATE_CODES,
    SIGNER_RELATIONSHIPS,
    TEMPLATE_EXTRA_FIELDS,
)
from app.modules.documents.schemas import (
    AnnulRequest,
    ConsentCreateRequest,
    ConsentPrefillOut,
    DocumentTemplateCreateRequest,
    ExtraFieldPrefill,
)
from app.modules.encounters import service as encounters_service
from app.modules.encounters.models import Encounter
from app.modules.iam.models import User
from app.modules.patients import service as patients_service
from app.modules.patients.models import Patient, PatientContact
from app.modules.patients.rules import calculate_age
from app.modules.treatment.models import ProcedurePlanned, TreatmentPlan

_SIGNER_RELATIONSHIP_LABELS = {"paciente": "Paciente", "tutor": "Tutor", "otro": "Otro"}
_SEX_LABELS: dict[str | None, str] = {
    "F": "Femenino",
    "M": "Masculino",
    "X": "Otro",
    None: "No especificado",
}

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


async def _get_guardian_contact(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> PatientContact | None:
    """Primer tutor/responsable registrado del paciente (PatientContact.role ==
    "guardian") -- cubre el tutor/parentesco que piden los formatos pediatricos
    (ver rules.TEMPLATE_EXTRA_FIELDS), sin necesitar un campo nuevo en el alta
    de paciente."""
    contacts = await patients_service.list_contacts(db, clinic_id=clinic_id, patient_id=patient_id)
    guardians = [c for c in contacts if c.role == "guardian"]
    return guardians[0] if guardians else None


def _hora_label(value: datetime | None) -> str:
    return value.strftime("%H:%M") if value else ""


async def _build_variables(
    db: AsyncSession,
    *,
    patient: Patient,
    encounter: Encounter,
    actor: User,
    procedure_name: str | None,
    plan_title: str | None,
    signer_name: str,
    witness1_name: str | None,
    witness2_name: str | None,
    extra_fields: dict[str, str],
    signed_at: datetime,
) -> dict[str, object]:
    """Variables disponibles en toda plantilla (`render_template`). Centraliza
    lo que antes armaba `create_consent` a mano, para que `build_consent_prefill`
    use exactamente los mismos datos de paciente/clinica/encuentro."""
    branding = await branding_service.get_branding(db)
    return {
        "paciente": {
            "nombre": patient.full_name,
            "edad": calculate_age(patient.date_of_birth, as_of=signed_at.date()),
            "sexo": _SEX_LABELS.get(patient.sex, "No especificado"),
            "fecha_nacimiento": patient.date_of_birth.strftime("%d/%m/%Y"),
            "expediente": patient.expediente_number,
        },
        "firmante": {"nombre": signer_name},
        "procedimiento": {"nombre": procedure_name} if procedure_name else "",
        "plan": {"titulo": plan_title} if plan_title else "",
        "clinica": {"nombre": branding.display_name},
        "fecha": signed_at.strftime("%d/%m/%Y %H:%M"),
        "profesional": {"nombre": actor.full_name, "cedula": actor.professional_license or ""},
        "encuentro": {
            "hora_entrada": _hora_label(encounter.started_at),
            "hora_salida": _hora_label(encounter.ended_at),
        },
        "testigos": {"uno": witness1_name or "", "dos": witness2_name or ""},
        "extra": extra_fields,
    }


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


async def seed_default_document_templates(
    db: AsyncSession, *, clinic_id: uuid.UUID, actor_id: uuid.UUID
) -> int:
    """Siembra los 24 formatos oficiales reales (default_templates.py) para una
    clinica, idempotente: si un codigo ya tiene una version `is_current`, lo
    salta (no crea una version nueva de algo que ya existe). Llamar DESPUES de
    `retire_legacy_example_templates` -- "endodoncia" es codigo real y de
    ejemplo a la vez, y solo queda sin version vigente tras ese retiro."""
    created = 0
    for code, name, html_content in DEFAULT_TEMPLATES:
        existing = (
            await db.execute(
                select(DocumentTemplate).where(
                    DocumentTemplate.clinic_id == clinic_id,
                    DocumentTemplate.code == code,
                    DocumentTemplate.is_current.is_(True),
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue
        await create_template_version(
            db,
            clinic_id=clinic_id,
            data=DocumentTemplateCreateRequest(code=code, name=name, html_content=html_content),
            actor_id=actor_id,
        )
        created += 1
    return created


async def retire_legacy_example_templates(
    db: AsyncSession, *, clinic_id: uuid.UUID, actor_id: uuid.UUID
) -> int:
    """Retira (is_current=False, SIN version de reemplazo) los 4 codigos de
    ejemplo ("Ejemplo -- validar con la clinica") que existian antes de
    integrar los 24 formatos reales -- regla 7 de CLAUDE.md: no se borran
    filas, un `Consent` ya firmado contra uno de estos sigue viendose igual
    por su `template_id` directo. Llamar ANTES de
    `seed_default_document_templates` (ver docstring de esa funcion)."""
    retired = 0
    for code in LEGACY_EXAMPLE_TEMPLATE_CODES:
        template = (
            await db.execute(
                select(DocumentTemplate).where(
                    DocumentTemplate.clinic_id == clinic_id,
                    DocumentTemplate.code == code,
                    DocumentTemplate.is_current.is_(True),
                )
            )
        ).scalar_one_or_none()
        if template is None:
            continue
        template.is_current = False
        retired += 1
        await audit_service.log(
            db,
            action="documents.template_retired",
            actor_user_id=actor_id,
            clinic_id=clinic_id,
            entity_type="document_template",
            entity_id=str(template.id),
            details={"code": code},
        )
    if retired:
        await db.commit()
    return retired


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

    missing_labels = [
        spec.label
        for spec in TEMPLATE_EXTRA_FIELDS.get(data.template_code, ())
        if spec.required and not (data.extra_fields.get(spec.key) or "").strip()
    ]
    if missing_labels:
        raise AppError(
            "MISSING_REQUIRED_FIELDS",
            "Faltan datos obligatorios para este formato: " + ", ".join(missing_labels),
            status_code=400,
        )

    signature_bytes = _decode_signature(data.signature_png_base64)

    signed_at = datetime.now(UTC)
    header = await get_pdf_header_info(db, storage, clinic_id=clinic_id)
    variables = await _build_variables(
        db,
        patient=patient,
        encounter=encounter,
        actor=actor,
        procedure_name=procedure_name,
        plan_title=plan_title,
        signer_name=data.signer_name,
        witness1_name=data.witness1_name,
        witness2_name=data.witness2_name,
        extra_fields=data.extra_fields,
        signed_at=signed_at,
    )

    try:
        pdf_bytes = build_consent_pdf(
            template_name=template.name,
            html_content=template.html_content,
            variables=variables,
            signature_png=signature_bytes,
            header=header,
            patient_name=patient.full_name,
            signer_name=data.signer_name,
            signer_relationship_label=_SIGNER_RELATIONSHIP_LABELS[data.signer_relationship],
            signed_at_label=signed_at.strftime("%d/%m/%Y %H:%M"),
            date_label=signed_at.strftime("%d/%m/%Y"),
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
        extra_fields=data.extra_fields or None,
        witness1_name=data.witness1_name,
        witness2_name=data.witness2_name,
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


async def build_consent_prefill(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    template_code: str,
    encounter_id: uuid.UUID,
    actor: User,
) -> ConsentPrefillOut:
    """Datos para el paso 2 del formulario de firma (ver ConsentsTab.tsx):
    que ya se puede prellenar y que le falta capturar al odontologo antes de
    firmar. No incluye `firmante`/`testigos` en `variables` (todavia no se
    conocen a esta altura del flujo, se llenan hasta el paso de firma)."""
    patient = await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    encounter = await _get_encounter_in_clinic(db, clinic_id=clinic_id, encounter_id=encounter_id)
    if encounter.patient_id != patient_id:
        raise AppError(
            "ENCOUNTER_PATIENT_MISMATCH",
            "La atencion no pertenece a este paciente",
            status_code=400,
        )
    branding = await branding_service.get_branding(db)
    now = datetime.now(UTC)
    variables: dict[str, object] = {
        "paciente": {
            "nombre": patient.full_name,
            "edad": calculate_age(patient.date_of_birth, as_of=now.date()),
            "sexo": _SEX_LABELS.get(patient.sex, "No especificado"),
            "fecha_nacimiento": patient.date_of_birth.strftime("%d/%m/%Y"),
            "expediente": patient.expediente_number,
        },
        "clinica": {"nombre": branding.display_name},
        "profesional": {"nombre": actor.full_name, "cedula": actor.professional_license or ""},
        "encuentro": {
            "hora_entrada": _hora_label(encounter.started_at),
            "hora_salida": _hora_label(encounter.ended_at),
        },
    }

    guardian = await _get_guardian_contact(db, clinic_id=clinic_id, patient_id=patient_id)
    if guardian is not None:
        variables["tutor"] = {
            "nombre": guardian.full_name,
            "parentesco": guardian.relationship_label or "",
        }

    extra_out: dict[str, ExtraFieldPrefill] = {}
    for spec in TEMPLATE_EXTRA_FIELDS.get(template_code, ()):
        value: str | None = None
        if spec.key == "tutor_parentesco" and guardian is not None:
            value = guardian.relationship_label
        elif spec.key == "diagnostico":
            notes = await encounters_service.list_encounter_notes(
                db, clinic_id=clinic_id, encounter_id=encounter_id
            )
            value = notes[-1].soap_a if notes else None
        extra_out[spec.key] = ExtraFieldPrefill(
            label=spec.label, required=spec.required, multiline=spec.multiline, value=value
        )

    return ConsentPrefillOut(variables=variables, extra_fields=extra_out)


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
