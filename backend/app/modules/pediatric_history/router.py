import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.core.storage import StorageBackend, get_storage_backend
from app.modules.iam.models import User
from app.modules.pediatric_history import service
from app.modules.pediatric_history.schemas import (
    AnnulRequest,
    PediatricBehaviorMaturityCreateRequest,
    PediatricBehaviorMaturityOut,
    PediatricEruptionDentitionCreateRequest,
    PediatricEruptionDentitionOut,
    PediatricOcclusionCreateRequest,
    PediatricOcclusionOut,
    PediatricOralHabitsCreateRequest,
    PediatricOralHabitsOut,
    PediatricPerinatalHistoryCreateRequest,
    PediatricPerinatalHistoryOut,
    PediatricToothAnnotationCreateRequest,
    PediatricToothAnnotationOut,
)

router = APIRouter(tags=["pediatric_history"])

_BASE = "/patients/{patient_id}/pediatric-history"


# --------------------------------------------------------------------------------
# 1. Antecedentes perinatales y primer ano de vida.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/perinatal-history", response_model=list[PediatricPerinatalHistoryOut])
async def list_perinatal_histories(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PediatricPerinatalHistoryOut]:
    items = await service.list_perinatal_histories(db, clinic_id=clinic_id, patient_id=patient_id)
    return [PediatricPerinatalHistoryOut.model_validate(i) for i in items]


@router.post(
    f"{_BASE}/perinatal-history", response_model=PediatricPerinatalHistoryOut, status_code=201
)
async def create_perinatal_history(
    patient_id: uuid.UUID,
    payload: PediatricPerinatalHistoryCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PediatricPerinatalHistoryOut:
    item = await service.create_perinatal_history(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return PediatricPerinatalHistoryOut.model_validate(item)


@router.post(
    f"{_BASE}/perinatal-history/{{item_id}}/annul", response_model=PediatricPerinatalHistoryOut
)
async def annul_perinatal_history(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PediatricPerinatalHistoryOut:
    item = await service.annul_perinatal_history(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return PediatricPerinatalHistoryOut.model_validate(item)


# --------------------------------------------------------------------------------
# 2. Habitos y antecedentes bucales.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/oral-habits", response_model=list[PediatricOralHabitsOut])
async def list_oral_habits(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PediatricOralHabitsOut]:
    items = await service.list_oral_habits(db, clinic_id=clinic_id, patient_id=patient_id)
    return [PediatricOralHabitsOut.model_validate(i) for i in items]


@router.post(f"{_BASE}/oral-habits", response_model=PediatricOralHabitsOut, status_code=201)
async def create_oral_habits(
    patient_id: uuid.UUID,
    payload: PediatricOralHabitsCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PediatricOralHabitsOut:
    item = await service.create_oral_habits(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return PediatricOralHabitsOut.model_validate(item)


@router.post(f"{_BASE}/oral-habits/{{item_id}}/annul", response_model=PediatricOralHabitsOut)
async def annul_oral_habits(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PediatricOralHabitsOut:
    item = await service.annul_oral_habits(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return PediatricOralHabitsOut.model_validate(item)


# --------------------------------------------------------------------------------
# 3. Madurez y conducta.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/behavior-maturity", response_model=list[PediatricBehaviorMaturityOut])
async def list_behavior_maturities(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PediatricBehaviorMaturityOut]:
    items = await service.list_behavior_maturities(db, clinic_id=clinic_id, patient_id=patient_id)
    return [PediatricBehaviorMaturityOut.model_validate(i) for i in items]


@router.post(
    f"{_BASE}/behavior-maturity", response_model=PediatricBehaviorMaturityOut, status_code=201
)
async def create_behavior_maturity(
    patient_id: uuid.UUID,
    payload: PediatricBehaviorMaturityCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PediatricBehaviorMaturityOut:
    item = await service.create_behavior_maturity(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return PediatricBehaviorMaturityOut.model_validate(item)


@router.post(
    f"{_BASE}/behavior-maturity/{{item_id}}/annul", response_model=PediatricBehaviorMaturityOut
)
async def annul_behavior_maturity(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PediatricBehaviorMaturityOut:
    item = await service.annul_behavior_maturity(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return PediatricBehaviorMaturityOut.model_validate(item)


# --------------------------------------------------------------------------------
# 4. Oclusion y alineamiento.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/occlusion", response_model=list[PediatricOcclusionOut])
async def list_occlusions(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PediatricOcclusionOut]:
    items = await service.list_occlusions(db, clinic_id=clinic_id, patient_id=patient_id)
    return [PediatricOcclusionOut.model_validate(i) for i in items]


@router.post(f"{_BASE}/occlusion", response_model=PediatricOcclusionOut, status_code=201)
async def create_occlusion(
    patient_id: uuid.UUID,
    payload: PediatricOcclusionCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PediatricOcclusionOut:
    item = await service.create_occlusion(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return PediatricOcclusionOut.model_validate(item)


@router.post(f"{_BASE}/occlusion/{{item_id}}/annul", response_model=PediatricOcclusionOut)
async def annul_occlusion(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PediatricOcclusionOut:
    item = await service.annul_occlusion(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return PediatricOcclusionOut.model_validate(item)


# --------------------------------------------------------------------------------
# 5. Erupcion y denticion.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/eruption-dentition", response_model=list[PediatricEruptionDentitionOut])
async def list_eruption_dentitions(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PediatricEruptionDentitionOut]:
    items = await service.list_eruption_dentitions(db, clinic_id=clinic_id, patient_id=patient_id)
    return [PediatricEruptionDentitionOut.model_validate(i) for i in items]


@router.post(
    f"{_BASE}/eruption-dentition", response_model=PediatricEruptionDentitionOut, status_code=201
)
async def create_eruption_dentition(
    patient_id: uuid.UUID,
    payload: PediatricEruptionDentitionCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PediatricEruptionDentitionOut:
    item = await service.create_eruption_dentition(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return PediatricEruptionDentitionOut.model_validate(item)


@router.post(
    f"{_BASE}/eruption-dentition/{{item_id}}/annul",
    response_model=PediatricEruptionDentitionOut,
)
async def annul_eruption_dentition(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PediatricEruptionDentitionOut:
    item = await service.annul_eruption_dentition(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return PediatricEruptionDentitionOut.model_validate(item)


# --------------------------------------------------------------------------------
# 6. Odontograma pediatrico -- anotaciones por pieza.
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/tooth-annotation", response_model=list[PediatricToothAnnotationOut])
async def list_tooth_annotations(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PediatricToothAnnotationOut]:
    items = await service.list_tooth_annotations(db, clinic_id=clinic_id, patient_id=patient_id)
    return [PediatricToothAnnotationOut.model_validate(i) for i in items]


@router.post(
    f"{_BASE}/tooth-annotation", response_model=PediatricToothAnnotationOut, status_code=201
)
async def create_tooth_annotation(
    patient_id: uuid.UUID,
    payload: PediatricToothAnnotationCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PediatricToothAnnotationOut:
    item = await service.create_tooth_annotation(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return PediatricToothAnnotationOut.model_validate(item)


@router.post(
    f"{_BASE}/tooth-annotation/{{item_id}}/annul", response_model=PediatricToothAnnotationOut
)
async def annul_tooth_annotation(
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> PediatricToothAnnotationOut:
    item = await service.annul_tooth_annotation(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return PediatricToothAnnotationOut.model_validate(item)


# --------------------------------------------------------------------------------
# PDF
# --------------------------------------------------------------------------------


@router.get(f"{_BASE}/pdf")
async def get_pediatric_history_pdf(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.read")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    pdf_bytes = await service.generate_pediatric_history_pdf(
        db, storage, clinic_id=clinic_id, patient_id=patient_id, actor_id=actor.id
    )
    filename = f"historia-clinica-pediatrica-{patient_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
