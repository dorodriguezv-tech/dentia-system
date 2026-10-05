import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.modules.diagnosis import service
from app.modules.diagnosis.schemas import AnnulRequest, DiagnosisCreateRequest, DiagnosisOut
from app.modules.iam.models import User

router = APIRouter(tags=["diagnosis"])


@router.get("/patients/{patient_id}/diagnoses", response_model=list[DiagnosisOut])
async def list_diagnoses(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("diagnosis.read")),
    db: AsyncSession = Depends(get_db),
) -> list[DiagnosisOut]:
    items = await service.list_diagnoses(db, clinic_id=clinic_id, patient_id=patient_id)
    return [DiagnosisOut.model_validate(i) for i in items]


@router.post("/patients/{patient_id}/diagnoses", response_model=DiagnosisOut, status_code=201)
async def create_diagnosis(
    patient_id: uuid.UUID,
    payload: DiagnosisCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("diagnosis.write")),
    db: AsyncSession = Depends(get_db),
) -> DiagnosisOut:
    item = await service.create_diagnosis(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return DiagnosisOut.model_validate(item)


@router.post("/patients/{patient_id}/diagnoses/{item_id}/annul", response_model=DiagnosisOut)
async def annul_diagnosis(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("diagnosis.write")),
    db: AsyncSession = Depends(get_db),
) -> DiagnosisOut:
    item = await service.annul_diagnosis(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return DiagnosisOut.model_validate(item)
