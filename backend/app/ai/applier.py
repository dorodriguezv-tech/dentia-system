"""Aplica una sugerencia de IA ya aceptada por el odontologo (docs/03_AGENTE_IA_VOZ.md
sec. 3). Nunca escribe directamente: siempre llama al servicio de dominio del modulo
correspondiente (regla 9 de CLAUDE.md), igual que si el dato viniera de un formulario
normal -- solo que con origin="AI_ASSISTED" (regla 10) y un AuditEvent AI_APPLY que
deja constancia del modelo y su digest."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import rules
from app.ai.models import AiSuggestion
from app.audit import service as audit_service
from app.core.errors import AppError
from app.modules.diagnosis import service as diagnosis_service
from app.modules.diagnosis.schemas import DiagnosisCreateRequest
from app.modules.encounters import service as encounters_service
from app.modules.encounters.models import ClinicalNote, Encounter
from app.modules.encounters.schemas import ClinicalNoteCreateRequest, ClinicalNoteUpdateRequest
from app.modules.odontogram import service as odontogram_service
from app.modules.odontogram.schemas import ToothFindingCreateRequest
from app.modules.records import service as records_service
from app.modules.records.schemas import (
    AllergyCreateRequest,
    MedicalHistoryCreateRequest,
    MedicationCreateRequest,
    VitalSignsCreateRequest,
)
from app.modules.treatment import service as treatment_service
from app.modules.treatment.models import TreatmentPhase, TreatmentPlan
from app.modules.treatment.schemas import (
    ItemCreateRequest,
    PhaseCreateRequest,
    PlanCreateRequest,
    ProcedurePerformedCreateRequest,
)

_NOTE_SECTION_FIELDS = {
    "S": "soap_s",
    "O": "soap_o",
    "A": "soap_a",
    "P": "soap_p",
    "free": "free_text",
}


async def _get_suggestion_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, suggestion_id: uuid.UUID
) -> AiSuggestion:
    suggestion = await db.get(AiSuggestion, suggestion_id)
    if suggestion is None or suggestion.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Sugerencia no encontrada", status_code=404)
    return suggestion


async def _get_or_create_draft_plan_and_phase(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    encounter_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> tuple[TreatmentPlan, TreatmentPhase]:
    """Las piezas planificadas por dictado necesitan un plan y una fase donde vivir,
    pero el dictado no especifica cual (docs sec. 4 solo da tooth_fdi/surfaces/
    procedure_code). Se reutiliza un plan en BORRADOR de esta atencion si ya existe, o
    se crea uno con una sola fase "General" -- ver docs/PENDIENTES_CLINICOS.md."""
    stmt = select(TreatmentPlan).where(
        TreatmentPlan.clinic_id == clinic_id,
        TreatmentPlan.patient_id == patient_id,
        TreatmentPlan.encounter_id == encounter_id,
        TreatmentPlan.status == "BORRADOR",
    )
    plan = (await db.execute(stmt)).scalars().first()
    if plan is None:
        plan = await treatment_service.create_plan(
            db,
            clinic_id=clinic_id,
            data=PlanCreateRequest(
                patient_id=patient_id,
                encounter_id=encounter_id,
                title="Propuesta del asistente de IA",
            ),
            actor_id=actor_id,
        )

    phase_stmt = (
        select(TreatmentPhase)
        .where(TreatmentPhase.plan_id == plan.id)
        .order_by(TreatmentPhase.sort_order)
    )
    phase = (await db.execute(phase_stmt)).scalars().first()
    if phase is None:
        phase = await treatment_service.add_phase(
            db,
            clinic_id=clinic_id,
            plan_id=plan.id,
            data=PhaseCreateRequest(name="General", sort_order=0, priority="media"),
            actor_id=actor_id,
        )
    return plan, phase


async def _get_or_create_draft_note(
    db: AsyncSession, *, clinic_id: uuid.UUID, encounter_id: uuid.UUID, actor_id: uuid.UUID
) -> ClinicalNote:
    stmt = (
        select(ClinicalNote)
        .where(ClinicalNote.clinic_id == clinic_id, ClinicalNote.encounter_id == encounter_id)
        .order_by(ClinicalNote.version.desc())
    )
    latest = (await db.execute(stmt)).scalars().first()
    if latest is not None and latest.status == "DRAFT":
        return latest
    return await encounters_service.create_note(
        db,
        clinic_id=clinic_id,
        encounter_id=encounter_id,
        data=ClinicalNoteCreateRequest(),
        author_id=actor_id,
    )


async def _apply_action(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    suggestion: AiSuggestion,
    data: dict[str, Any],
    actor_id: uuid.UUID,
) -> str | None:
    """Aplica la accion y devuelve el id de la entidad creada (si aplica)."""
    action_type = suggestion.action_type
    patient_id = suggestion.patient_id
    encounter_id = suggestion.encounter_id

    if action_type == "set_chief_complaint":
        encounter = await db.get(Encounter, encounter_id)
        assert encounter is not None
        encounter.chief_complaint = data["text"]
        await db.commit()
        return str(encounter.id)

    if action_type == "add_allergy":
        allergy = await records_service.create_allergy(
            db,
            clinic_id=clinic_id,
            patient_id=patient_id,
            data=AllergyCreateRequest(
                encounter_id=encounter_id,
                substance=data["substance"],
                reaction=data.get("reaction"),
                severity=data.get("severity", "leve"),
            ),
            actor_id=actor_id,
            origin="AI_ASSISTED",
        )
        return str(allergy.id)

    if action_type == "add_medication":
        medication = await records_service.create_medication(
            db,
            clinic_id=clinic_id,
            patient_id=patient_id,
            data=MedicationCreateRequest(
                encounter_id=encounter_id,
                name=data["name"],
                dose=data.get("dose"),
                frequency=data.get("frequency"),
            ),
            actor_id=actor_id,
            origin="AI_ASSISTED",
        )
        return str(medication.id)

    if action_type == "add_medical_history":
        history = await records_service.create_history(
            db,
            clinic_id=clinic_id,
            patient_id=patient_id,
            data=MedicalHistoryCreateRequest(
                encounter_id=encounter_id, category=data["category"], text=data["text"]
            ),
            actor_id=actor_id,
            origin="AI_ASSISTED",
        )
        return str(history.id)

    if action_type == "add_vital_signs":
        vital_signs = await records_service.create_vital_signs(
            db,
            clinic_id=clinic_id,
            patient_id=patient_id,
            data=VitalSignsCreateRequest(
                encounter_id=encounter_id,
                bp_systolic=data.get("bp_sys"),
                bp_diastolic=data.get("bp_dia"),
                heart_rate=data.get("hr"),
                temperature=data.get("temp"),
            ),
            actor_id=actor_id,
            origin="AI_ASSISTED",
        )
        return str(vital_signs.id)

    if action_type == "add_tooth_finding":
        surfaces = data.get("surfaces") or [None]
        last_id = None
        for surface in surfaces:
            finding = await odontogram_service.create_finding(
                db,
                clinic_id=clinic_id,
                data=ToothFindingCreateRequest(
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                    tooth_fdi=data["tooth_fdi"],
                    surface=surface,
                    finding_code=data["finding_code"],
                    kind="EXISTING",
                    material=data.get("material"),
                ),
                actor_id=actor_id,
                origin="AI_ASSISTED",
            )
            last_id = str(finding.id)
        return last_id

    if action_type == "add_planned_procedure":
        plan, phase = await _get_or_create_draft_plan_and_phase(
            db,
            clinic_id=clinic_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            actor_id=actor_id,
        )
        surfaces = data.get("surfaces") or [None]
        last_id = None
        for surface in surfaces:
            planned_item = await treatment_service.add_item(
                db,
                clinic_id=clinic_id,
                plan_id=plan.id,
                phase_id=phase.id,
                data=ItemCreateRequest(
                    encounter_id=encounter_id,
                    tooth_fdi=data.get("tooth_fdi"),
                    surface=surface,
                    procedure_code=data["procedure_code"],
                ),
                actor_id=actor_id,
                origin="AI_ASSISTED",
            )
            last_id = str(planned_item.id)
        return last_id

    if action_type == "add_performed_procedure":
        surfaces = data.get("surfaces") or [None]
        last_id = None
        for surface in surfaces:
            performed, _amount = await treatment_service.register_performed(
                db,
                clinic_id=clinic_id,
                data=ProcedurePerformedCreateRequest(
                    patient_id=patient_id,
                    encounter_id=encounter_id,
                    tooth_fdi=data.get("tooth_fdi"),
                    surface=surface,
                    procedure_code=data["procedure_code"],
                ),
                actor_id=actor_id,
                origin="AI_ASSISTED",
            )
            last_id = str(performed.id)
        return last_id

    if action_type == "add_diagnosis":
        diagnosis_item = await diagnosis_service.create_diagnosis(
            db,
            clinic_id=clinic_id,
            patient_id=patient_id,
            data=DiagnosisCreateRequest(
                encounter_id=encounter_id,
                tooth_fdi=data.get("tooth_fdi"),
                code=data.get("diagnosis_code"),
                text=data["text"],
            ),
            actor_id=actor_id,
            origin="AI_ASSISTED",
        )
        return str(diagnosis_item.id)

    if action_type == "append_note":
        note = await _get_or_create_draft_note(
            db, clinic_id=clinic_id, encounter_id=encounter_id, actor_id=actor_id
        )
        field = _NOTE_SECTION_FIELDS[data["section"]]
        previous = getattr(note, field) or ""
        new_value = f"{previous}\n{data['text']}".strip() if previous else data["text"]
        updated = await encounters_service.update_note(
            db,
            clinic_id=clinic_id,
            note_id=note.id,
            data=ClinicalNoteUpdateRequest(**{field: new_value}),
            actor_id=actor_id,
        )
        return str(updated.id)

    if action_type == "schedule_followup":
        # "Agenda (solo propuesta)" (docs sec. 4): no hay suficiente contexto para crear
        # una cita real (profesional, gabinete, horario); aceptar solo deja constancia
        # de que el odontologo revizo y confirmo la recomendacion -- ver
        # docs/PENDIENTES_CLINICOS.md.
        return None

    raise AppError(
        "UNKNOWN_ACTION_TYPE", f"Tipo de accion desconocido: {action_type}", status_code=500
    )


async def accept_suggestion(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    edits: dict[str, Any] | None,
    actor_id: uuid.UUID,
    confirmation_mode: str = "touch",
) -> tuple[AiSuggestion, str | None]:
    """`confirmation_mode` (docs/05_ASISTENTE_DENTIA_VOZ_CONVERSACIONAL.md sec. 9):
    "touch" es el panel de Propuestas de la Fase 8 (default); Dentia (Fase 13,
    Parte C) pasa "voice_implicit" (nivel 2, cuenta regresiva) o
    "voice_explicit" (nivel 3, "si"). Devuelve tambien el id de la entidad
    creada -- Dentia lo necesita para la pila de deshacer (sec. 6.5)."""
    suggestion = await _get_suggestion_in_clinic(
        db, clinic_id=clinic_id, suggestion_id=suggestion_id
    )
    if not rules.is_editable(suggestion.status):
        raise AppError(
            "SUGGESTION_NOT_PENDING",
            "Solo una sugerencia pendiente se puede aceptar",
            status_code=409,
        )

    data = {**suggestion.payload, **(edits or {})}
    entity_id = await _apply_action(
        db, clinic_id=clinic_id, suggestion=suggestion, data=data, actor_id=actor_id
    )

    suggestion.status = "ACCEPTED"
    suggestion.reviewed_at = datetime.now(UTC)
    suggestion.reviewed_by = actor_id
    if edits:
        suggestion.payload = data

    await audit_service.log(
        db,
        action="ai.suggestion_accepted",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type=suggestion.action_type,
        entity_id=entity_id,
        details={
            "suggestion_id": str(suggestion.id),
            "model": suggestion.model_name,
            "model_digest": suggestion.model_digest,
            "edited": bool(edits),
            "confirmation_mode": confirmation_mode,
        },
    )
    await db.commit()
    return suggestion, entity_id


async def reject_suggestion(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    reason: str | None,
    actor_id: uuid.UUID,
) -> AiSuggestion:
    suggestion = await _get_suggestion_in_clinic(
        db, clinic_id=clinic_id, suggestion_id=suggestion_id
    )
    if not rules.is_editable(suggestion.status):
        raise AppError(
            "SUGGESTION_NOT_PENDING",
            "Solo una sugerencia pendiente se puede rechazar",
            status_code=409,
        )

    suggestion.status = "REJECTED"
    suggestion.reviewed_at = datetime.now(UTC)
    suggestion.reviewed_by = actor_id
    suggestion.reject_reason = reason

    await audit_service.log(
        db,
        action="ai.suggestion_rejected",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="ai_suggestion",
        entity_id=str(suggestion.id),
        details={"reason": reason},
    )
    await db.commit()
    return suggestion
