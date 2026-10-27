import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.core.storage import StorageBackend, get_storage_backend
from app.modules.iam.models import User
from app.modules.records import rules, service
from app.modules.records.schemas import (
    AllergyCreateRequest,
    AllergyOut,
    AnnulRequest,
    FamilyHistoryEntryCreateRequest,
    FamilyHistoryEntryOut,
    MedicalHistoryCreateRequest,
    MedicalHistoryOut,
    MedicationCreateRequest,
    MedicationOut,
    PersonalNonPathologicalHistoryCreateRequest,
    PersonalNonPathologicalHistoryOut,
    PersonalPathologicalHistoryCreateRequest,
    PersonalPathologicalHistoryOut,
    SystemsReviewEntryCreateRequest,
    SystemsReviewEntryOut,
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


def _vital_signs_out(item: object) -> VitalSignsOut:
    out = VitalSignsOut.model_validate(item)
    out.body_mass_index = rules.body_mass_index(out.height_m, out.weight_kg)
    return out


@router.get("/patients/{patient_id}/vital-signs", response_model=list[VitalSignsOut])
async def list_vital_signs(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[VitalSignsOut]:
    items = await service.list_vital_signs(db, clinic_id=clinic_id, patient_id=patient_id)
    return [_vital_signs_out(i) for i in items]


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
    return _vital_signs_out(item)


# --------------------------------------------------------------------------------
# Fase A (rediseno del expediente, docs/clinica): Historia Clinica General.
# --------------------------------------------------------------------------------


@router.get(
    "/patients/{patient_id}/general-history/family",
    response_model=list[FamilyHistoryEntryOut],
)
async def list_family_history(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[FamilyHistoryEntryOut]:
    items = await service.list_family_history(db, clinic_id=clinic_id, patient_id=patient_id)
    return [FamilyHistoryEntryOut.model_validate(i) for i in items]


@router.post(
    "/patients/{patient_id}/general-history/family",
    response_model=FamilyHistoryEntryOut,
    status_code=201,
)
async def create_family_history(
    patient_id: uuid.UUID,
    payload: FamilyHistoryEntryCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> FamilyHistoryEntryOut:
    item = await service.create_family_history_entry(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return FamilyHistoryEntryOut.model_validate(item)


@router.post(
    "/patients/{patient_id}/general-history/family/{item_id}/annul",
    response_model=FamilyHistoryEntryOut,
)
async def annul_family_history(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> FamilyHistoryEntryOut:
    item = await service.annul_family_history_entry(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return FamilyHistoryEntryOut.model_validate(item)


@router.get(
    "/patients/{patient_id}/general-history/pathological",
    response_model=list[PersonalPathologicalHistoryOut],
)
async def list_pathological_history(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PersonalPathologicalHistoryOut]:
    items = await service.list_pathological_history(db, clinic_id=clinic_id, patient_id=patient_id)
    return [PersonalPathologicalHistoryOut.model_validate(i) for i in items]


@router.post(
    "/patients/{patient_id}/general-history/pathological",
    response_model=PersonalPathologicalHistoryOut,
    status_code=201,
)
async def create_pathological_history(
    patient_id: uuid.UUID,
    payload: PersonalPathologicalHistoryCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PersonalPathologicalHistoryOut:
    item = await service.create_pathological_history(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return PersonalPathologicalHistoryOut.model_validate(item)


@router.post(
    "/patients/{patient_id}/general-history/pathological/{item_id}/annul",
    response_model=PersonalPathologicalHistoryOut,
)
async def annul_pathological_history(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PersonalPathologicalHistoryOut:
    item = await service.annul_pathological_history(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return PersonalPathologicalHistoryOut.model_validate(item)


@router.get(
    "/patients/{patient_id}/general-history/non-pathological",
    response_model=list[PersonalNonPathologicalHistoryOut],
)
async def list_non_pathological_history(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PersonalNonPathologicalHistoryOut]:
    items = await service.list_non_pathological_history(
        db, clinic_id=clinic_id, patient_id=patient_id
    )
    return [PersonalNonPathologicalHistoryOut.model_validate(i) for i in items]


@router.post(
    "/patients/{patient_id}/general-history/non-pathological",
    response_model=PersonalNonPathologicalHistoryOut,
    status_code=201,
)
async def create_non_pathological_history(
    patient_id: uuid.UUID,
    payload: PersonalNonPathologicalHistoryCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PersonalNonPathologicalHistoryOut:
    item = await service.create_non_pathological_history(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return PersonalNonPathologicalHistoryOut.model_validate(item)


@router.post(
    "/patients/{patient_id}/general-history/non-pathological/{item_id}/annul",
    response_model=PersonalNonPathologicalHistoryOut,
)
async def annul_non_pathological_history(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PersonalNonPathologicalHistoryOut:
    item = await service.annul_non_pathological_history(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return PersonalNonPathologicalHistoryOut.model_validate(item)


@router.get(
    "/patients/{patient_id}/general-history/systems-review",
    response_model=list[SystemsReviewEntryOut],
)
async def list_systems_review(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[SystemsReviewEntryOut]:
    items = await service.list_systems_review(db, clinic_id=clinic_id, patient_id=patient_id)
    return [SystemsReviewEntryOut.model_validate(i) for i in items]


@router.post(
    "/patients/{patient_id}/general-history/systems-review",
    response_model=SystemsReviewEntryOut,
    status_code=201,
)
async def create_systems_review(
    patient_id: uuid.UUID,
    payload: SystemsReviewEntryCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> SystemsReviewEntryOut:
    item = await service.create_systems_review(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return SystemsReviewEntryOut.model_validate(item)


@router.post(
    "/patients/{patient_id}/general-history/systems-review/{item_id}/annul",
    response_model=SystemsReviewEntryOut,
)
async def annul_systems_review(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> SystemsReviewEntryOut:
    item = await service.annul_systems_review(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return SystemsReviewEntryOut.model_validate(item)


@router.get("/patients/{patient_id}/general-history/pdf")
async def get_general_history_pdf(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    pdf_bytes = await service.generate_general_history_pdf(
        db, storage, clinic_id=clinic_id, patient_id=patient_id, actor_id=actor.id
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="historia-clinica-general-{patient_id}.pdf"'
        },
    )


@router.get("/patients/{patient_id}/alerts", response_model=list[str])
async def get_patient_alerts(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    return await service.get_patient_alerts(db, clinic_id=clinic_id, patient_id=patient_id)
