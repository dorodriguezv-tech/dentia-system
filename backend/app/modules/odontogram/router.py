import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.modules.iam.models import User
from app.modules.odontogram import service
from app.modules.odontogram.schemas import (
    ToothFindingCreateRequest,
    ToothFindingHistoryEntryOut,
    ToothFindingOut,
)

router = APIRouter(tags=["odontogram"])


@router.get("/patients/{patient_id}/odontogram", response_model=list[ToothFindingOut])
async def get_odontogram(
    patient_id: uuid.UUID,
    at: date | None = Query(default=None),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("odontogram.read")),
    db: AsyncSession = Depends(get_db),
) -> list[ToothFindingOut]:
    if at is None:
        items = await service.get_current_odontogram(db, clinic_id=clinic_id, patient_id=patient_id)
    else:
        items = await service.get_odontogram_at(
            db, clinic_id=clinic_id, patient_id=patient_id, at=at
        )
    return [ToothFindingOut.model_validate(i) for i in items]


@router.post("/tooth-findings", response_model=ToothFindingOut, status_code=201)
async def create_tooth_finding(
    payload: ToothFindingCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("odontogram.write")),
    db: AsyncSession = Depends(get_db),
) -> ToothFindingOut:
    item = await service.create_finding(db, clinic_id=clinic_id, data=payload, actor_id=actor.id)
    return ToothFindingOut.model_validate(item)


@router.get(
    "/patients/{patient_id}/teeth/{tooth_fdi}/history",
    response_model=list[ToothFindingHistoryEntryOut],
)
async def get_tooth_history(
    patient_id: uuid.UUID,
    tooth_fdi: int,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("odontogram.read")),
    db: AsyncSession = Depends(get_db),
) -> list[ToothFindingHistoryEntryOut]:
    rows = await service.get_tooth_history(
        db, clinic_id=clinic_id, patient_id=patient_id, tooth_fdi=tooth_fdi
    )
    return [
        ToothFindingHistoryEntryOut(
            id=row.id,
            encounter_id=row.encounter_id,
            tooth_fdi=row.tooth_fdi,
            surface=row.surface,
            finding_code=row.finding_code,
            kind=row.kind,
            material=row.material,
            supersedes_id=row.supersedes_id,
            is_current=row.is_current,
            origin=row.origin,
            created_at=row.created_at,
            author_name=author_name,
        )
        for row, author_name in rows
    ]
