import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.modules.iam.models import User
from app.modules.records import service
from app.modules.records.schemas import (
    AllergyCreateRequest,
    AllergyOut,
    AnnulRequest,
    MedicalHistoryCreateRequest,
    MedicalHistoryOut,
    MedicationCreateRequest,
    MedicationOut,
    VitalSignsCreateRequest,
    VitalSignsOut,
)

router = APIRouter(tags=["records"])


@router.get("/patients/{patient_id}/history", response_model=list[MedicalHistoryOut])
async def list_history(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[MedicalHistoryOut]:
    items = await service.list_history(db, clinic_id=clinic_id, patient_id=patient_id)
    return [MedicalHistoryOut.model_validate(i) for i in items]


@router.post("/patients/{patient_id}/history", response_model=MedicalHistoryOut, status_code=201)
async def create_history(
    patient_id: uuid.UUID,
    payload: MedicalHistoryCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> MedicalHistoryOut:
    item = await service.create_history(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return MedicalHistoryOut.model_validate(item)


@router.post("/patients/{patient_id}/history/{item_id}/annul", response_model=MedicalHistoryOut)
async def annul_history(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> MedicalHistoryOut:
    item = await service.annul_history(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return MedicalHistoryOut.model_validate(item)


@router.get("/patients/{patient_id}/allergies", response_model=list[AllergyOut])
async def list_allergies(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[AllergyOut]:
    items = await service.list_allergies(db, clinic_id=clinic_id, patient_id=patient_id)
    return [AllergyOut.model_validate(i) for i in items]


@router.post("/patients/{patient_id}/allergies", response_model=AllergyOut, status_code=201)
async def create_allergy(
    patient_id: uuid.UUID,
    payload: AllergyCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> AllergyOut:
    item = await service.create_allergy(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return AllergyOut.model_validate(item)


@router.post("/patients/{patient_id}/allergies/{item_id}/annul", response_model=AllergyOut)
async def annul_allergy(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> AllergyOut:
    item = await service.annul_allergy(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return AllergyOut.model_validate(item)


@router.get("/patients/{patient_id}/medications", response_model=list[MedicationOut])
async def list_medications(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[MedicationOut]:
    items = await service.list_medications(db, clinic_id=clinic_id, patient_id=patient_id)
    return [MedicationOut.model_validate(i) for i in items]


@router.post("/patients/{patient_id}/medications", response_model=MedicationOut, status_code=201)
async def create_medication(
    patient_id: uuid.UUID,
    payload: MedicationCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> MedicationOut:
    item = await service.create_medication(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return MedicationOut.model_validate(item)


@router.post("/patients/{patient_id}/medications/{item_id}/annul", response_model=MedicationOut)
async def annul_medication(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> MedicationOut:
    item = await service.annul_medication(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return MedicationOut.model_validate(item)


@router.get("/patients/{patient_id}/vital-signs", response_model=list[VitalSignsOut])
async def list_vital_signs(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[VitalSignsOut]:
    items = await service.list_vital_signs(db, clinic_id=clinic_id, patient_id=patient_id)
    return [VitalSignsOut.model_validate(i) for i in items]


@router.post("/patients/{patient_id}/vital-signs", response_model=VitalSignsOut, status_code=201)
async def create_vital_signs(
    patient_id: uuid.UUID,
    payload: VitalSignsCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> VitalSignsOut:
    item = await service.create_vital_signs(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return VitalSignsOut.model_validate(item)


@router.get("/patients/{patient_id}/alerts", response_model=list[str])
async def get_patient_alerts(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    return await service.get_patient_alerts(db, clinic_id=clinic_id, patient_id=patient_id)
