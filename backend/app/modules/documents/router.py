import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.core.storage import StorageBackend, get_storage_backend
from app.modules.documents import service
from app.modules.documents.schemas import (
    AnnulRequest,
    ConsentCreateRequest,
    ConsentOut,
    DocumentTemplateCreateRequest,
    DocumentTemplateOut,
)
from app.modules.iam.models import User

router = APIRouter(tags=["documents"])


@router.get("/document-templates", response_model=list[DocumentTemplateOut])
async def list_templates(
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("documents.read")),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentTemplateOut]:
    items = await service.list_templates(db, clinic_id=clinic_id)
    return [DocumentTemplateOut.model_validate(i) for i in items]


@router.get("/document-templates/{code}/history", response_model=list[DocumentTemplateOut])
async def get_template_history(
    code: str,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("documents.read")),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentTemplateOut]:
    items = await service.get_template_history(db, clinic_id=clinic_id, code=code)
    return [DocumentTemplateOut.model_validate(i) for i in items]


@router.post("/document-templates", response_model=DocumentTemplateOut, status_code=201)
async def create_template_version(
    payload: DocumentTemplateCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("documents.write")),
    db: AsyncSession = Depends(get_db),
) -> DocumentTemplateOut:
    template = await service.create_template_version(
        db, clinic_id=clinic_id, data=payload, actor_id=actor.id
    )
    return DocumentTemplateOut.model_validate(template)


@router.get("/patients/{patient_id}/consents", response_model=list[ConsentOut])
async def list_consents(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("documents.read")),
    db: AsyncSession = Depends(get_db),
) -> list[ConsentOut]:
    items = await service.list_consents(db, clinic_id=clinic_id, patient_id=patient_id)
    return [ConsentOut.model_validate(i) for i in items]


@router.post("/patients/{patient_id}/consents", response_model=ConsentOut, status_code=201)
async def create_consent(
    patient_id: uuid.UUID,
    payload: ConsentCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("documents.sign")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> ConsentOut:
    consent = await service.create_consent(
        db, storage, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor=actor
    )
    return ConsentOut.model_validate(consent)


@router.get("/consents/{consent_id}/pdf")
async def get_consent_pdf(
    consent_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("documents.read")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    pdf_bytes = await service.get_consent_pdf(
        db, storage, clinic_id=clinic_id, consent_id=consent_id, actor_id=actor.id
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="consentimiento-{consent_id}.pdf"'},
    )


@router.post("/consents/{consent_id}/annul", response_model=ConsentOut)
async def annul_consent(
    consent_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("documents.write")),
    db: AsyncSession = Depends(get_db),
) -> ConsentOut:
    consent = await service.annul_consent(
        db, clinic_id=clinic_id, consent_id=consent_id, data=payload, actor_id=actor.id
    )
    return ConsentOut.model_validate(consent)
