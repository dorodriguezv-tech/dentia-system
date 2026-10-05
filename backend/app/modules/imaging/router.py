import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.core.errors import AppError
from app.core.storage import StorageBackend, get_storage_backend
from app.modules.iam.models import User
from app.modules.imaging import service
from app.modules.imaging.schemas import AnnulRequest, ImageOut, StudyType

router = APIRouter(tags=["imaging"])


def _image_out(image) -> ImageOut:  # type: ignore[no-untyped-def]
    return ImageOut(
        id=image.id,
        encounter_id=image.encounter_id,
        study_type=image.study_type,
        tooth_fdi=image.tooth_fdi,
        procedure_planned_id=image.procedure_planned_id,
        procedure_performed_id=image.procedure_performed_id,
        content_type=image.content_type,
        original_filename=image.original_filename,
        notes=image.notes,
        has_thumbnail=image.thumbnail_path is not None,
        is_active=image.is_active,
        created_at=image.created_at,
    )


@router.post("/patients/{patient_id}/images", response_model=list[ImageOut], status_code=201)
async def upload_images(
    patient_id: uuid.UUID,
    encounter_id: uuid.UUID = Form(...),
    study_type: StudyType = Form(...),
    tooth_fdi: int | None = Form(default=None),
    procedure_planned_id: uuid.UUID | None = Form(default=None),
    procedure_performed_id: uuid.UUID | None = Form(default=None),
    notes: str | None = Form(default=None),
    files: list[UploadFile] = File(...),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("imaging.write")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> list[ImageOut]:
    uploaded = [
        service.UploadedFile(
            filename=f.filename or "archivo",
            content_type=f.content_type or "application/octet-stream",
            data=await f.read(),
        )
        for f in files
    ]
    items = await service.upload_images(
        db,
        storage,
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=encounter_id,
        study_type=study_type,
        tooth_fdi=tooth_fdi,
        procedure_planned_id=procedure_planned_id,
        procedure_performed_id=procedure_performed_id,
        notes=notes,
        files=uploaded,
        actor_id=actor.id,
    )
    return [_image_out(i) for i in items]


@router.get("/patients/{patient_id}/images", response_model=list[ImageOut])
async def list_images(
    patient_id: uuid.UUID,
    study_type: StudyType | None = Query(default=None),
    tooth_fdi: int | None = Query(default=None),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("imaging.read")),
    db: AsyncSession = Depends(get_db),
) -> list[ImageOut]:
    items = await service.list_images(
        db, clinic_id=clinic_id, patient_id=patient_id, study_type=study_type, tooth_fdi=tooth_fdi
    )
    return [_image_out(i) for i in items]


@router.get("/images/{image_id}")
async def get_image(
    image_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("imaging.read")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    data, content_type = await service.read_image(
        db, storage, clinic_id=clinic_id, image_id=image_id, actor_id=actor.id
    )
    return Response(content=data, media_type=content_type)


@router.get("/images/{image_id}/thumbnail")
async def get_thumbnail(
    image_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("imaging.read")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    data = await service.read_thumbnail(db, storage, clinic_id=clinic_id, image_id=image_id)
    if data is None:
        raise AppError("NOT_FOUND", "Esta imagen no tiene miniatura", status_code=404)
    return Response(content=data, media_type="image/jpeg")


@router.post("/images/{image_id}/annul", response_model=ImageOut)
async def annul_image(
    image_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("imaging.write")),
    db: AsyncSession = Depends(get_db),
) -> ImageOut:
    image = await service.annul_image(
        db, clinic_id=clinic_id, image_id=image_id, reason=payload.reason, actor_id=actor.id
    )
    return _image_out(image)
