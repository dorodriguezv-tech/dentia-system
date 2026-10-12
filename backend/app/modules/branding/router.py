import uuid

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.core.storage import StorageBackend, get_storage_backend
from app.modules.branding import service
from app.modules.branding.schemas import BrandingOut, BrandingUpdateRequest
from app.modules.iam.models import User

router = APIRouter(tags=["branding"])


@router.get("/branding", response_model=BrandingOut)
async def get_branding(db: AsyncSession = Depends(get_db)) -> BrandingOut:
    return await service.get_branding(db)


@router.put("/branding", response_model=BrandingOut)
async def update_branding(
    payload: BrandingUpdateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("branding.manage")),
    db: AsyncSession = Depends(get_db),
) -> BrandingOut:
    return await service.update_branding(db, clinic_id=clinic_id, data=payload, actor_id=actor.id)


@router.post("/branding/logo", response_model=BrandingOut)
async def upload_logo(
    file: UploadFile,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("branding.manage")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> BrandingOut:
    data = await file.read()
    return await service.upload_logo(
        db,
        storage,
        clinic_id=clinic_id,
        filename=file.filename or "logo",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        actor_id=actor.id,
    )


@router.get("/branding/logo")
async def get_logo(
    db: AsyncSession = Depends(get_db), storage: StorageBackend = Depends(get_storage_backend)
) -> Response:
    # W2: siempre hay algo que mostrar (el propio o el de DENT-IA por defecto).
    data, content_type = await service.read_logo(db, storage)
    return Response(content=data, media_type=content_type)


@router.get("/branding/favicon")
async def get_favicon(
    db: AsyncSession = Depends(get_db), storage: StorageBackend = Depends(get_storage_backend)
) -> Response:
    data, content_type = await service.read_favicon(db, storage)
    return Response(content=data, media_type=content_type)
