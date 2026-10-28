import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import AppError
from app.core.storage import StorageBackend
from app.modules.clinical_documents.models import CounterReferralNote, Prescription, ReferralNote
from app.modules.clinical_documents.pdf import (
    CounterReferralPdfData,
    PatientHeaderPdfData,
    PrescriptionMedicationRow,
    PrescriptionPdfData,
    ReferralPdfData,
    build_counter_referral_pdf,
    build_prescription_pdf,
    build_referral_pdf,
)
from app.modules.clinical_documents.rules import (
    allergy_summary,
    next_folio,
    vital_signs_summary_values,
)
from app.modules.clinical_documents.schemas import (
    AnnulRequest,
    CounterReferralNoteCreateRequest,
    PrescriptionCreateRequest,
    ReferralNoteCreateRequest,
)
from app.modules.documents.pdf_header import get_pdf_header_info
from app.modules.encounters.models import Encounter
from app.modules.iam.models import Clinic, User
from app.modules.patients.models import Patient
from app.modules.patients.rules import calculate_age
from app.modules.records.service import list_allergies, list_vital_signs

_SEX_LABELS: dict[str | None, str] = {
    "F": "Femenino",
    "M": "Masculino",
    "X": "Otro",
    None: "No especificado",
}


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


def _annul(
    item: Prescription | ReferralNote | CounterReferralNote, data: AnnulRequest, actor_id: uuid.UUID
) -> None:
    item.is_active = False
    item.annul_reason = data.reason
    item.annulled_by = actor_id
    item.annulled_at = datetime.now(UTC)


async def _vitals_and_allergies(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> tuple[dict[str, str], list[str]]:
    """Signos vitales vigentes (el mas reciente) y alergias activas del
    paciente -- autollenado en vivo (regla 8 de CLAUDE.md), nunca duplicado
    en las tablas nuevas de este modulo (ver docstring de Prescription)."""
    vitals_list = await list_vital_signs(db, clinic_id=clinic_id, patient_id=patient_id)
    latest = vitals_list[0] if vitals_list else None
    vitals = vital_signs_summary_values(
        height_m=latest.height_m if latest else None,
        weight_kg=latest.weight_kg if latest else None,
        temperature=latest.temperature if latest else None,
        bp_systolic=latest.bp_systolic if latest else None,
        bp_diastolic=latest.bp_diastolic if latest else None,
    )
    allergies = [
        a.substance
        for a in await list_allergies(db, clinic_id=clinic_id, patient_id=patient_id)
        if a.is_active
    ]
    return vitals, allergies


# --------------------------------------------------------------------------- receta


async def _next_prescription_folio(db: AsyncSession, *, clinic_id: uuid.UUID) -> str:
    """Folio consecutivo simple por clinica (decision documentada en
    rules.py::next_folio): se cuenta cuantas recetas existen ya para esa
    clinica (anuladas incluidas, para que el folio nunca se repita aunque se
    anule una receta) y se arma "RX-NNNNNN". No es el UUID de la fila para
    que sea corto y legible en el papel impreso."""
    count = (
        await db.execute(select(func.count()).where(Prescription.clinic_id == clinic_id))
    ).scalar_one()
    return next_folio(count)


async def create_prescription(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: PrescriptionCreateRequest,
    actor: User,
) -> Prescription:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    encounter = await _get_encounter_in_clinic(
        db, clinic_id=clinic_id, encounter_id=data.encounter_id
    )
    if encounter.patient_id != patient_id:
        raise AppError(
            "ENCOUNTER_PATIENT_MISMATCH",
            "La atencion no pertenece a este paciente",
            status_code=400,
        )

    folio = await _next_prescription_folio(db, clinic_id=clinic_id)
    item = Prescription(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        folio=folio,
        diagnostico=data.diagnostico,
        medications=[m.model_dump() for m in data.medications],
        created_by=actor.id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="clinical_documents.prescription_created",
        actor_user_id=actor.id,
        clinic_id=clinic_id,
        entity_type="prescription",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id), "folio": folio},
    )
    await db.commit()
    return item


async def list_prescriptions(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[Prescription]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(Prescription)
        .where(Prescription.clinic_id == clinic_id, Prescription.patient_id == patient_id)
        .order_by(Prescription.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def _get_prescription_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, item_id: uuid.UUID
) -> Prescription:
    item = await db.get(Prescription, item_id)
    if item is None or item.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Receta no encontrada", status_code=404)
    return item


async def annul_prescription(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> Prescription:
    item = await _get_prescription_in_clinic(db, clinic_id=clinic_id, item_id=item_id)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="clinical_documents.prescription_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="prescription",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


async def get_prescription_pdf(
    db: AsyncSession,
    storage: StorageBackend,
    *,
    clinic_id: uuid.UUID,
    item_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> bytes:
    item = await _get_prescription_in_clinic(db, clinic_id=clinic_id, item_id=item_id)
    patient = await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=item.patient_id)
    clinic = await db.get(Clinic, clinic_id)
    professional = await db.get(User, item.created_by) if item.created_by else None
    header = await get_pdf_header_info(db, storage, clinic_id=clinic_id)
    vitals, allergy_labels = await _vitals_and_allergies(
        db, clinic_id=clinic_id, patient_id=item.patient_id
    )
    has_allergies, allergies_label = allergy_summary(allergy_labels)

    data = PrescriptionPdfData(
        header=header,
        date_label=item.created_at.strftime("%d/%m/%Y"),
        folio=item.folio,
        patient_name=patient.full_name,
        patient_birth_date_label=patient.date_of_birth.strftime("%d/%m/%Y"),
        patient_age=calculate_age(patient.date_of_birth, as_of=item.created_at.date()),
        patient_sex_label=_SEX_LABELS.get(patient.sex, "No especificado"),
        allergies_label=(f"Si: {allergies_label}" if has_allergies else "No"),
        talla=vitals["talla"],
        peso=vitals["peso"],
        imc=vitals["imc"],
        temperatura=vitals["temperatura"],
        tension=vitals["tension"],
        diagnostico=item.diagnostico,
        medications=[
            PrescriptionMedicationRow(nombre=m["nombre"], detalle=m["detalle"])
            for m in item.medications
        ],
        professional_name=professional.full_name if professional else "",
        professional_license=(professional.professional_license or "") if professional else "",
        clinic_address=clinic.address or "" if clinic else "",
        clinic_phone=clinic.phone or "" if clinic else "",
    )
    pdf_bytes = build_prescription_pdf(data)

    await audit_service.log(
        db,
        action="clinical_documents.prescription_pdf_read",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="prescription",
        entity_id=str(item_id),
    )
    await db.commit()
    return pdf_bytes


# ------------------------------------------------------- referencia / contrarreferencia


async def _patient_header_data(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient: Patient
) -> PatientHeaderPdfData:
    vitals, _allergy_labels = await _vitals_and_allergies(
        db, clinic_id=clinic_id, patient_id=patient.id
    )
    return PatientHeaderPdfData(
        patient_name=patient.full_name,
        patient_address=patient.address or "",
        patient_phone=patient.phone or "",
        talla=vitals["talla"],
        peso=vitals["peso"],
        imc=vitals["imc"],
        temperatura=vitals["temperatura"],
        tension=vitals["tension"],
    )


async def create_referral_note(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: ReferralNoteCreateRequest,
    actor: User,
) -> ReferralNote:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    encounter = await _get_encounter_in_clinic(
        db, clinic_id=clinic_id, encounter_id=data.encounter_id
    )
    if encounter.patient_id != patient_id:
        raise AppError(
            "ENCOUNTER_PATIENT_MISMATCH",
            "La atencion no pertenece a este paciente",
            status_code=400,
        )

    item = ReferralNote(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        diagnosticos=data.diagnosticos,
        medicamentos_texto=data.medicamentos_texto,
        alergias_texto=data.alergias_texto,
        tratamientos_texto=data.tratamientos_texto,
        observaciones=data.observaciones,
        motivo_interconsulta=data.motivo_interconsulta,
        establecimiento_receptor=data.establecimiento_receptor,
        created_by=actor.id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="clinical_documents.referral_note_created",
        actor_user_id=actor.id,
        clinic_id=clinic_id,
        entity_type="referral_note",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def list_referral_notes(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[ReferralNote]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(ReferralNote)
        .where(ReferralNote.clinic_id == clinic_id, ReferralNote.patient_id == patient_id)
        .order_by(ReferralNote.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def _get_referral_note_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, item_id: uuid.UUID
) -> ReferralNote:
    item = await db.get(ReferralNote, item_id)
    if item is None or item.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Hoja de referencia no encontrada", status_code=404)
    return item


async def annul_referral_note(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> ReferralNote:
    item = await _get_referral_note_in_clinic(db, clinic_id=clinic_id, item_id=item_id)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="clinical_documents.referral_note_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="referral_note",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


async def get_referral_note_pdf(
    db: AsyncSession,
    storage: StorageBackend,
    *,
    clinic_id: uuid.UUID,
    item_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> bytes:
    item = await _get_referral_note_in_clinic(db, clinic_id=clinic_id, item_id=item_id)
    patient = await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=item.patient_id)
    professional = await db.get(User, item.created_by) if item.created_by else None
    header = await get_pdf_header_info(db, storage, clinic_id=clinic_id)
    patient_header = await _patient_header_data(db, clinic_id=clinic_id, patient=patient)

    data = ReferralPdfData(
        patient=patient_header,
        diagnosticos=item.diagnosticos,
        medicamentos_texto=item.medicamentos_texto,
        alergias_texto=item.alergias_texto,
        tratamientos_texto=item.tratamientos_texto,
        observaciones=item.observaciones,
        motivo_interconsulta=item.motivo_interconsulta,
        establecimiento_receptor=item.establecimiento_receptor,
        dentist_name=professional.full_name if professional else "",
        date_label=item.created_at.strftime("%d/%m/%Y"),
    )
    pdf_bytes = build_referral_pdf(header, data)

    await audit_service.log(
        db,
        action="clinical_documents.referral_note_pdf_read",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="referral_note",
        entity_id=str(item_id),
    )
    await db.commit()
    return pdf_bytes


async def create_counter_referral_note(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: CounterReferralNoteCreateRequest,
    actor: User,
) -> CounterReferralNote:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    encounter = await _get_encounter_in_clinic(
        db, clinic_id=clinic_id, encounter_id=data.encounter_id
    )
    if encounter.patient_id != patient_id:
        raise AppError(
            "ENCOUNTER_PATIENT_MISMATCH",
            "La atencion no pertenece a este paciente",
            status_code=400,
        )
    if data.referral_note_id is not None:
        referral = await db.get(ReferralNote, data.referral_note_id)
        if referral is None or referral.clinic_id != clinic_id or referral.patient_id != patient_id:
            raise AppError("NOT_FOUND", "Hoja de referencia no encontrada", status_code=404)

    item = CounterReferralNote(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        referral_note_id=data.referral_note_id,
        motivo_contrarreferencia=data.motivo_contrarreferencia,
        tratamientos_texto=data.tratamientos_texto,
        observaciones=data.observaciones,
        motivo_interconsulta_original=data.motivo_interconsulta_original,
        establecimiento_emisor=data.establecimiento_emisor,
        created_by=actor.id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="clinical_documents.counter_referral_note_created",
        actor_user_id=actor.id,
        clinic_id=clinic_id,
        entity_type="counter_referral_note",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def list_counter_referral_notes(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[CounterReferralNote]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(CounterReferralNote)
        .where(
            CounterReferralNote.clinic_id == clinic_id, CounterReferralNote.patient_id == patient_id
        )
        .order_by(CounterReferralNote.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def _get_counter_referral_note_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, item_id: uuid.UUID
) -> CounterReferralNote:
    item = await db.get(CounterReferralNote, item_id)
    if item is None or item.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Hoja de contrarreferencia no encontrada", status_code=404)
    return item


async def annul_counter_referral_note(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> CounterReferralNote:
    item = await _get_counter_referral_note_in_clinic(db, clinic_id=clinic_id, item_id=item_id)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="clinical_documents.counter_referral_note_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="counter_referral_note",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


async def get_counter_referral_note_pdf(
    db: AsyncSession,
    storage: StorageBackend,
    *,
    clinic_id: uuid.UUID,
    item_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> bytes:
    item = await _get_counter_referral_note_in_clinic(db, clinic_id=clinic_id, item_id=item_id)
    patient = await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=item.patient_id)
    professional = await db.get(User, item.created_by) if item.created_by else None
    header = await get_pdf_header_info(db, storage, clinic_id=clinic_id)
    patient_header = await _patient_header_data(db, clinic_id=clinic_id, patient=patient)

    data = CounterReferralPdfData(
        patient=patient_header,
        motivo_contrarreferencia=item.motivo_contrarreferencia,
        tratamientos_texto=item.tratamientos_texto,
        observaciones=item.observaciones,
        motivo_interconsulta_original=item.motivo_interconsulta_original,
        establecimiento_emisor=item.establecimiento_emisor,
        dentist_name=professional.full_name if professional else "",
        date_label=item.created_at.strftime("%d/%m/%Y"),
    )
    pdf_bytes = build_counter_referral_pdf(header, data)

    await audit_service.log(
        db,
        action="clinical_documents.counter_referral_note_pdf_read",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="counter_referral_note",
        entity_id=str(item_id),
    )
    await db.commit()
    return pdf_bytes
