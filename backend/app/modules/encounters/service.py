import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import AiSuggestion
from app.audit import service as audit_service
from app.core.errors import AppError
from app.modules.agenda import rules as agenda_rules
from app.modules.agenda.models import Appointment
from app.modules.agenda.schemas import StatusChangeRequest
from app.modules.encounters import rules
from app.modules.encounters.models import ClinicalNote, Encounter
from app.modules.encounters.schemas import (
    CancelNoteRequest,
    ClinicalNoteCreateRequest,
    ClinicalNoteUpdateRequest,
    CorrectNoteRequest,
    EncounterCreateRequest,
    FinalizeNoteRequest,
    TimelineEntryOut,
    TimelineNoteOut,
)
from app.modules.iam.models import User
from app.modules.patients.models import Patient
from app.modules.records.service import get_patient_alerts


async def _get_patient_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> Patient:
    patient = await db.get(Patient, patient_id)
    if patient is None or patient.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Paciente no encontrado", status_code=404)
    return patient


async def get_encounter(
    db: AsyncSession, *, clinic_id: uuid.UUID, encounter_id: uuid.UUID
) -> Encounter:
    encounter = await db.get(Encounter, encounter_id)
    if encounter is None or encounter.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Atencion no encontrada", status_code=404)
    return encounter


async def create_encounter(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    data: EncounterCreateRequest,
    professional_id: uuid.UUID,
) -> Encounter:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=data.patient_id)

    encounter = Encounter(
        clinic_id=clinic_id,
        patient_id=data.patient_id,
        professional_id=professional_id,
        appointment_id=data.appointment_id,
        chief_complaint=data.chief_complaint,
        started_at=datetime.now(UTC),
        created_by=professional_id,
    )
    db.add(encounter)
    await db.flush()

    await audit_service.log(
        db,
        action="encounters.created",
        actor_user_id=professional_id,
        clinic_id=clinic_id,
        entity_type="encounter",
        entity_id=str(encounter.id),
        details={"patient_id": str(data.patient_id)},
    )
    await db.commit()
    return encounter


async def get_current_encounter(
    db: AsyncSession, *, clinic_id: uuid.UUID, professional_id: uuid.UUID
) -> tuple[Encounter, str] | None:
    """B10 (docs/06_APP_MOVIL_V1_1_PARIDAD.md sec. 4): la atencion que ese
    profesional dejo abierta, para la barra "En consulta" del movil y recuperarla
    al reabrir la app.

    Limitacion conocida (docs/PENDIENTES_CLINICOS.md #51): todavia no existe un
    "cerrar consulta" real (B11, M6) que marque `Encounter.ended_at`, asi que por
    ahora esto se limita a las atenciones iniciadas HOY (hora local de la
    sucursal) -- si no, "la mas reciente con ended_at NULL" seria SIEMPRE la
    atencion mas reciente de ese profesional sin importar que tan vieja, porque
    ended_at nunca se escribe en ningun lado todavia. Cuando B11 exista, quitar
    el limite de "hoy" y dejar solo `ended_at IS NULL` (para poder recuperar una
    consulta que de verdad quedo abierta de un dia para otro).

    Import diferido de `app.voice.dialogue` (mismo helper de zona horaria que ya
    usa Dentia) para evitar un import circular: ese modulo ya importa
    `encounters.service` a nivel de modulo.
    """
    from app.voice.dialogue import _clinic_zoneinfo, _local_day_bounds_utc

    tz = await _clinic_zoneinfo(db, clinic_id=clinic_id)
    today = datetime.now(tz).date()
    day_start, day_end = _local_day_bounds_utc(tz, today)

    stmt = (
        select(Encounter, Patient.full_name)
        .join(Patient, Patient.id == Encounter.patient_id)
        .where(
            Encounter.clinic_id == clinic_id,
            Encounter.professional_id == professional_id,
            Encounter.ended_at.is_(None),
            Encounter.started_at >= day_start,
            Encounter.started_at < day_end,
        )
        .order_by(Encounter.started_at.desc())
        .limit(1)
    )
    row = (await db.execute(stmt)).first()
    return (row[0], row[1]) if row else None


async def close_encounter(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    encounter_id: uuid.UUID,
    alerts_acknowledged: bool,
    actor_id: uuid.UUID,
) -> Encounter:
    """B11 (docs/06_APP_MOVIL_V1_1_PARIDAD.md sec. 4, M6): "Cerrar consulta" en el
    movil. Devuelve un `code` estable por cada validacion para que la app muestre
    el mensaje adecuado (propuestas de IA pendientes, alertas sin revisar, nota sin
    finalizar) -- mismo criterio de `code` estable que el resto de AppError.

    No valida "procedimientos sin pieza" (mencionado en el documento de paridad):
    `ProcedurePerformed.tooth_fdi` es legitimamente nulo para procedimientos
    generales (ver treatment/router.py, tooth_label "General"), asi que no hay una
    regla clara de cuando es un error de captura vs. un procedimiento sin pieza a
    proposito -- pendiente de validar con la clinica (docs/PENDIENTES_CLINICOS.md).
    """
    encounter = await get_encounter(db, clinic_id=clinic_id, encounter_id=encounter_id)
    if encounter.ended_at is not None:
        raise AppError("ENCOUNTER_ALREADY_CLOSED", "Esta atencion ya esta cerrada", status_code=409)

    pending_stmt = select(func.count()).where(
        AiSuggestion.encounter_id == encounter_id, AiSuggestion.status == "PENDING"
    )
    pending_count = (await db.execute(pending_stmt)).scalar_one()
    if pending_count:
        raise AppError(
            "AI_SUGGESTIONS_PENDING",
            f"Tienes {pending_count} propuesta(s) del asistente sin revisar",
            details={"count": pending_count},
            status_code=400,
        )

    alerts = await get_patient_alerts(db, clinic_id=clinic_id, patient_id=encounter.patient_id)
    if alerts and not alerts_acknowledged:
        raise AppError(
            "ALERTS_NOT_ACKNOWLEDGED",
            "El paciente tiene alertas criticas; confirma haberlas revisado antes de cerrar",
            details={"alerts": alerts},
            status_code=400,
        )

    final_note_stmt = select(func.count()).where(
        ClinicalNote.encounter_id == encounter_id, ClinicalNote.status == "FINAL"
    )
    has_final_note = (await db.execute(final_note_stmt)).scalar_one() > 0
    if not has_final_note:
        raise AppError(
            "NOTE_NOT_FINALIZED",
            "Finaliza la nota de la consulta antes de cerrarla",
            status_code=400,
        )

    encounter.ended_at = datetime.now(UTC)

    if encounter.appointment_id is not None:
        appointment = await db.get(Appointment, encounter.appointment_id)
        if appointment is not None and agenda_rules.can_transition(appointment.status, "TERMINADA"):
            # Import diferido (mismo motivo que get_current_encounter): agenda.service
            # ya importa encounters.service a nivel de modulo.
            from app.modules.agenda import service as agenda_service

            await agenda_service.change_status(
                db,
                clinic_id=clinic_id,
                appointment_id=appointment.id,
                data=StatusChangeRequest(status="TERMINADA"),
                actor_id=actor_id,
            )

    await audit_service.log(
        db,
        action="encounters.closed",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="encounter",
        entity_id=str(encounter.id),
    )
    await db.commit()
    return encounter


async def list_patient_encounters(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[Encounter]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(Encounter)
        .where(Encounter.clinic_id == clinic_id, Encounter.patient_id == patient_id)
        .order_by(Encounter.started_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def _get_note_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, note_id: uuid.UUID
) -> ClinicalNote:
    note = await db.get(ClinicalNote, note_id)
    if note is None or note.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Nota no encontrada", status_code=404)
    return note


async def create_note(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    encounter_id: uuid.UUID,
    data: ClinicalNoteCreateRequest,
    author_id: uuid.UUID,
) -> ClinicalNote:
    encounter = await get_encounter(db, clinic_id=clinic_id, encounter_id=encounter_id)

    note = ClinicalNote(
        clinic_id=clinic_id,
        encounter_id=encounter.id,
        patient_id=encounter.patient_id,
        author_id=author_id,
        status="DRAFT",
        soap_s=data.soap_s,
        soap_o=data.soap_o,
        soap_a=data.soap_a,
        soap_p=data.soap_p,
        free_text=data.free_text,
        version=1,
        created_by=author_id,
    )
    db.add(note)
    await db.commit()
    return note


async def list_encounter_notes(
    db: AsyncSession, *, clinic_id: uuid.UUID, encounter_id: uuid.UUID
) -> list[ClinicalNote]:
    await get_encounter(db, clinic_id=clinic_id, encounter_id=encounter_id)
    stmt = (
        select(ClinicalNote)
        .where(ClinicalNote.clinic_id == clinic_id, ClinicalNote.encounter_id == encounter_id)
        .order_by(ClinicalNote.version)
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_note(db: AsyncSession, *, clinic_id: uuid.UUID, note_id: uuid.UUID) -> ClinicalNote:
    return await _get_note_in_clinic(db, clinic_id=clinic_id, note_id=note_id)


async def update_note(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    note_id: uuid.UUID,
    data: ClinicalNoteUpdateRequest,
    actor_id: uuid.UUID,
) -> ClinicalNote:
    note = await _get_note_in_clinic(db, clinic_id=clinic_id, note_id=note_id)
    if not rules.is_editable(note.status):
        raise AppError(
            "NOTE_NOT_EDITABLE",
            "Una nota que no esta en borrador no se puede editar",
            status_code=403,
        )

    for field in ("soap_s", "soap_o", "soap_a", "soap_p", "free_text"):
        value = getattr(data, field)
        if value is not None:
            setattr(note, field, value)

    await db.commit()
    return note


async def finalize_note(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    note_id: uuid.UUID,
    data: FinalizeNoteRequest,
    actor_id: uuid.UUID,
) -> ClinicalNote:
    note = await _get_note_in_clinic(db, clinic_id=clinic_id, note_id=note_id)
    if not rules.can_transition(note.status, "FINAL"):
        raise AppError(
            "INVALID_TRANSITION",
            f"No se puede finalizar una nota en estado {note.status}",
            status_code=409,
        )

    alerts = await get_patient_alerts(db, clinic_id=clinic_id, patient_id=note.patient_id)
    if alerts and not data.alerts_acknowledged:
        raise AppError(
            "ALERTS_NOT_ACKNOWLEDGED",
            "El paciente tiene alertas criticas; confirma haberlas revisado antes de finalizar",
            details={"alerts": alerts},
            status_code=400,
        )

    note.content_hash = rules.compute_content_hash(
        note.soap_s, note.soap_o, note.soap_a, note.soap_p, note.free_text
    )
    note.status = "FINAL"
    note.finalized_at = datetime.now(UTC)
    note.finalized_by = actor_id

    await audit_service.log(
        db,
        action="encounters.note_finalized",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="clinical_note",
        entity_id=str(note.id),
        details={"content_hash": note.content_hash},
    )
    await db.commit()
    return note


async def correct_note(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    note_id: uuid.UUID,
    data: CorrectNoteRequest,
    actor_id: uuid.UUID,
) -> ClinicalNote:
    old_note = await _get_note_in_clinic(db, clinic_id=clinic_id, note_id=note_id)
    if not rules.can_transition(old_note.status, "CORRECTED"):
        raise AppError(
            "INVALID_TRANSITION",
            f"No se puede corregir una nota en estado {old_note.status}",
            status_code=409,
        )

    old_note.status = "CORRECTED"

    new_note = ClinicalNote(
        clinic_id=clinic_id,
        encounter_id=old_note.encounter_id,
        patient_id=old_note.patient_id,
        author_id=actor_id,
        status="DRAFT",
        soap_s=old_note.soap_s,
        soap_o=old_note.soap_o,
        soap_a=old_note.soap_a,
        soap_p=old_note.soap_p,
        free_text=old_note.free_text,
        version=old_note.version + 1,
        previous_version_id=old_note.id,
        correction_reason=data.reason,
        created_by=actor_id,
    )
    db.add(new_note)

    await audit_service.log(
        db,
        action="encounters.note_corrected",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="clinical_note",
        entity_id=str(old_note.id),
        details={"reason": data.reason},
    )
    await db.commit()
    return new_note


async def cancel_note(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    note_id: uuid.UUID,
    data: CancelNoteRequest,
    actor_id: uuid.UUID,
) -> ClinicalNote:
    note = await _get_note_in_clinic(db, clinic_id=clinic_id, note_id=note_id)
    if not rules.can_transition(note.status, "CANCELLED"):
        raise AppError(
            "INVALID_TRANSITION",
            f"No se puede cancelar una nota en estado {note.status}",
            status_code=409,
        )

    note.status = "CANCELLED"
    note.cancel_reason = data.reason
    note.cancelled_at = datetime.now(UTC)
    note.cancelled_by = actor_id

    await audit_service.log(
        db,
        action="encounters.note_cancelled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="clinical_note",
        entity_id=str(note.id),
        details={"reason": data.reason},
    )
    await db.commit()
    return note


async def get_patient_timeline(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[TimelineEntryOut]:
    encounters = await list_patient_encounters(db, clinic_id=clinic_id, patient_id=patient_id)

    entries: list[TimelineEntryOut] = []
    for encounter in encounters:
        professional = await db.get(User, encounter.professional_id)
        notes = await list_encounter_notes(db, clinic_id=clinic_id, encounter_id=encounter.id)
        entries.append(
            TimelineEntryOut(
                encounter_id=encounter.id,
                started_at=encounter.started_at,
                chief_complaint=encounter.chief_complaint,
                professional_name=professional.full_name if professional else "",
                notes=[
                    TimelineNoteOut(
                        id=n.id, status=n.status, version=n.version, finalized_at=n.finalized_at
                    )
                    for n in notes
                ],
            )
        )
    return entries
