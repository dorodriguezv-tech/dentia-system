import uuid
from typing import Literal

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.db import get_db
from app.core.deps import get_clinic_id, get_current_user, require_permission
from app.core.errors import AppError
from app.core.storage import StorageBackend, get_storage_backend
from app.modules.document_settings import service
from app.modules.document_settings.schemas import DocumentSettingsOut, DocumentSettingsUpdateRequest
from app.modules.iam.models import User

router = APIRouter(tags=["document_settings"])

Side = Literal["left", "right"]


@router.get("/document-settings", response_model=DocumentSettingsOut)
async def get_document_settings(
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DocumentSettingsOut:
    # Cualquier rol autenticado puede leer (lo necesitan los PDFs y la
    # pantalla de administracion, CLAUDE.md sec. 5/9 -- la escritura si queda
    # restringida a admin_clinica/superadmin via document_settings.manage).
    return await service.get_document_settings(db, clinic_id=clinic_id)


@router.put("/document-settings", response_model=DocumentSettingsOut)
async def update_document_settings(
    payload: DocumentSettingsUpdateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("document_settings.manage")),
    db: AsyncSession = Depends(get_db),
) -> DocumentSettingsOut:
    return await service.update_document_settings(
        db, clinic_id=clinic_id, data=payload, actor_id=actor.id
    )


@router.post("/document-settings/logo-{side}", response_model=DocumentSettingsOut)
async def upload_logo(
    side: Side,
    file: UploadFile,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("document_settings.manage")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> DocumentSettingsOut:
    data = await file.read()
    return await service.upload_logo(
        db,
        storage,
        clinic_id=clinic_id,
        side=side,
        content_type=file.content_type or "application/octet-stream",
        data=data,
        actor_id=actor.id,
    )


@router.get("/document-settings/logo-{side}")
async def get_logo(
    side: Side,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    asset = await service.read_logo(db, storage, clinic_id=clinic_id, side=side)
    if asset is None:
        raise AppError("NOT_FOUND", "No hay un logo configurado de ese lado", status_code=404)
    data, content_type = asset
    return Response(content=data, media_type=content_type)
