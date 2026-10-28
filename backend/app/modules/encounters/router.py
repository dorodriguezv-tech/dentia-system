import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.core.storage import StorageBackend, get_storage_backend
from app.modules.encounters import service
from app.modules.encounters.schemas import (
    CancelNoteRequest,
    ClinicalNoteCreateRequest,
    ClinicalNoteOut,
    ClinicalNoteUpdateRequest,
    CorrectNoteRequest,
    CurrentEncounterOut,
    EncounterCloseRequest,
    EncounterCreateRequest,
    EncounterOut,
    FinalizeNoteRequest,
    TimelineEntryOut,
)
from app.modules.iam.models import User

router = APIRouter(tags=["encounters"])


@router.post("/encounters", response_model=EncounterOut, status_code=201)
async def create_encounter(
    payload: EncounterCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> EncounterOut:
    encounter = await service.create_encounter(
        db, clinic_id=clinic_id, data=payload, professional_id=actor.id
    )
    return EncounterOut.model_validate(encounter)


@router.get("/encounters/current", response_model=CurrentEncounterOut | None)
async def get_current_encounter(
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> CurrentEncounterOut | None:
    result = await service.get_current_encounter(db, clinic_id=clinic_id, professional_id=actor.id)
    if result is None:
        return None
    encounter, patient_full_name = result
    return CurrentEncounterOut(
        id=encounter.id,
        patient_id=encounter.patient_id,
        patient_full_name=patient_full_name,
        started_at=encounter.started_at,
        chief_complaint=encounter.chief_complaint,
    )


@router.get("/encounters/{encounter_id}", response_model=EncounterOut)
async def get_encounter(
    encounter_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> EncounterOut:
    encounter = await service.get_encounter(db, clinic_id=clinic_id, encounter_id=encounter_id)
    return EncounterOut.model_validate(encounter)


@router.post("/encounters/{encounter_id}/close", response_model=EncounterOut)
async def close_encounter(
    encounter_id: uuid.UUID,
    payload: EncounterCloseRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> EncounterOut:
    encounter = await service.close_encounter(
        db,
        clinic_id=clinic_id,
        encounter_id=encounter_id,
        alerts_acknowledged=payload.alerts_acknowledged,
        actor_id=actor.id,
    )
    return EncounterOut.model_validate(encounter)


@router.get("/patients/{patient_id}/encounters", response_model=list[EncounterOut])
async def list_patient_encounters(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[EncounterOut]:
    encounters = await service.list_patient_encounters(
        db, clinic_id=clinic_id, patient_id=patient_id
    )
    return [EncounterOut.model_validate(e) for e in encounters]


@router.get("/patients/{patient_id}/timeline", response_model=list[TimelineEntryOut])
async def get_patient_timeline(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[TimelineEntryOut]:
    return await service.get_patient_timeline(db, clinic_id=clinic_id, patient_id=patient_id)


@router.post("/encounters/{encounter_id}/notes", response_model=ClinicalNoteOut, status_code=201)
async def create_note(
    encounter_id: uuid.UUID,
    payload: ClinicalNoteCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> ClinicalNoteOut:
    note = await service.create_note(
        db, clinic_id=clinic_id, encounter_id=encounter_id, data=payload, author_id=actor.id
    )
    return ClinicalNoteOut.model_validate(note)


@router.get("/encounters/{encounter_id}/notes", response_model=list[ClinicalNoteOut])
async def list_encounter_notes(
    encounter_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[ClinicalNoteOut]:
    notes = await service.list_encounter_notes(db, clinic_id=clinic_id, encounter_id=encounter_id)
    return [ClinicalNoteOut.model_validate(n) for n in notes]


@router.get("/notes/{note_id}", response_model=ClinicalNoteOut)
async def get_note(
    note_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> ClinicalNoteOut:
    note = await service.get_note(db, clinic_id=clinic_id, note_id=note_id)
    return ClinicalNoteOut.model_validate(note)


@router.patch("/notes/{note_id}", response_model=ClinicalNoteOut)
async def update_note(
    note_id: uuid.UUID,
    payload: ClinicalNoteUpdateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> ClinicalNoteOut:
    note = await service.update_note(
        db, clinic_id=clinic_id, note_id=note_id, data=payload, actor_id=actor.id
    )
    return ClinicalNoteOut.model_validate(note)


@router.post("/notes/{note_id}/finalize", response_model=ClinicalNoteOut)
async def finalize_note(
    note_id: uuid.UUID,
    payload: FinalizeNoteRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> ClinicalNoteOut:
    note = await service.finalize_note(
        db, clinic_id=clinic_id, note_id=note_id, data=payload, actor_id=actor.id
    )
    return ClinicalNoteOut.model_validate(note)


@router.post("/notes/{note_id}/correct", response_model=ClinicalNoteOut)
async def correct_note(
    note_id: uuid.UUID,
    payload: CorrectNoteRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> ClinicalNoteOut:
    note = await service.correct_note(
        db, clinic_id=clinic_id, note_id=note_id, data=payload, actor_id=actor.id
    )
    return ClinicalNoteOut.model_validate(note)


@router.get("/notes/{note_id}/pdf")
async def get_note_pdf(
    note_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    pdf_bytes = await service.generate_note_pdf(
        db, storage, clinic_id=clinic_id, note_id=note_id, actor_id=actor.id
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="nota-evolucion-{note_id}.pdf"'},
    )


@router.post("/notes/{note_id}/cancel", response_model=ClinicalNoteOut)
async def cancel_note(
    note_id: uuid.UUID,
    payload: CancelNoteRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> ClinicalNoteOut:
    note = await service.cancel_note(
        db, clinic_id=clinic_id, note_id=note_id, data=payload, actor_id=actor.id
    )
    return ClinicalNoteOut.model_validate(note)
