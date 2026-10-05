import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.modules.billing import service
from app.modules.billing.schemas import ChargeOut
from app.modules.iam.models import User

router = APIRouter(tags=["billing"])


@router.get("/patients/{patient_id}/charges", response_model=list[ChargeOut])
async def list_charges(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("billing.read")),
    db: AsyncSession = Depends(get_db),
) -> list[ChargeOut]:
    items = await service.list_charges(db, clinic_id=clinic_id, patient_id=patient_id)
    return [ChargeOut.model_validate(i) for i in items]
