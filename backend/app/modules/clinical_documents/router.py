import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.core.storage import StorageBackend, get_storage_backend
from app.modules.clinical_documents import service
from app.modules.clinical_documents.schemas import (
    AnnulRequest,
    CounterReferralNoteCreateRequest,
    CounterReferralNoteOut,
    PrescriptionCreateRequest,
    PrescriptionOut,
    ReferralNoteCreateRequest,
    ReferralNoteOut,
)
from app.modules.iam.models import User

router = APIRouter(tags=["clinical-documents"])


# --------------------------------------------------------------------------- receta


@router.get(
    "/patients/{patient_id}/clinical-documents/prescriptions", response_model=list[PrescriptionOut]
)
async def list_prescriptions(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("documents.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PrescriptionOut]:
    items = await service.list_prescriptions(db, clinic_id=clinic_id, patient_id=patient_id)
    return [PrescriptionOut.model_validate(i) for i in items]


@router.post(
    "/patients/{patient_id}/clinical-documents/prescriptions",
    response_model=PrescriptionOut,
    status_code=201,
)
async def create_prescription(
    patient_id: uuid.UUID,
    payload: PrescriptionCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("documents.write")),
    db: AsyncSession = Depends(get_db),
) -> PrescriptionOut:
    item = await service.create_prescription(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor=actor
    )
    return PrescriptionOut.model_validate(item)


@router.get("/clinical-documents/prescriptions/{item_id}/pdf")
async def get_prescription_pdf(
    item_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("documents.read")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    pdf_bytes = await service.get_prescription_pdf(
        db, storage, clinic_id=clinic_id, item_id=item_id, actor_id=actor.id
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="receta-{item_id}.pdf"'},
    )


@router.post("/clinical-documents/prescriptions/{item_id}/annul", response_model=PrescriptionOut)
async def annul_prescription(
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("documents.write")),
    db: AsyncSession = Depends(get_db),
) -> PrescriptionOut:
    item = await service.annul_prescription(
        db, clinic_id=clinic_id, item_id=item_id, data=payload, actor_id=actor.id
    )
    return PrescriptionOut.model_validate(item)


# --------------------------------------------------------------------------- referencia


@router.get(
    "/patients/{patient_id}/clinical-documents/referral-notes", response_model=list[ReferralNoteOut]
)
async def list_referral_notes(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("documents.read")),
    db: AsyncSession = Depends(get_db),
) -> list[ReferralNoteOut]:
    items = await service.list_referral_notes(db, clinic_id=clinic_id, patient_id=patient_id)
    return [ReferralNoteOut.model_validate(i) for i in items]


@router.post(
    "/patients/{patient_id}/clinical-documents/referral-notes",
    response_model=ReferralNoteOut,
    status_code=201,
)
async def create_referral_note(
    patient_id: uuid.UUID,
    payload: ReferralNoteCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("documents.write")),
    db: AsyncSession = Depends(get_db),
) -> ReferralNoteOut:
    item = await service.create_referral_note(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor=actor
    )
    return ReferralNoteOut.model_validate(item)


@router.get("/clinical-documents/referral-notes/{item_id}/pdf")
async def get_referral_note_pdf(
    item_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("documents.read")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    pdf_bytes = await service.get_referral_note_pdf(
        db, storage, clinic_id=clinic_id, item_id=item_id, actor_id=actor.id
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="referencia-{item_id}.pdf"'},
    )


@router.post("/clinical-documents/referral-notes/{item_id}/annul", response_model=ReferralNoteOut)
async def annul_referral_note(
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("documents.write")),
    db: AsyncSession = Depends(get_db),
) -> ReferralNoteOut:
    item = await service.annul_referral_note(
        db, clinic_id=clinic_id, item_id=item_id, data=payload, actor_id=actor.id
    )
    return ReferralNoteOut.model_validate(item)


# ------------------------------------------------------------------- contrarreferencia


@router.get(
    "/patients/{patient_id}/clinical-documents/counter-referral-notes",
    response_model=list[CounterReferralNoteOut],
)
async def list_counter_referral_notes(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("documents.read")),
    db: AsyncSession = Depends(get_db),
) -> list[CounterReferralNoteOut]:
    items = await service.list_counter_referral_notes(
        db, clinic_id=clinic_id, patient_id=patient_id
    )
    return [CounterReferralNoteOut.model_validate(i) for i in items]


@router.post(
    "/patients/{patient_id}/clinical-documents/counter-referral-notes",
    response_model=CounterReferralNoteOut,
    status_code=201,
)
async def create_counter_referral_note(
    patient_id: uuid.UUID,
    payload: CounterReferralNoteCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("documents.write")),
    db: AsyncSession = Depends(get_db),
) -> CounterReferralNoteOut:
    item = await service.create_counter_referral_note(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor=actor
    )
    return CounterReferralNoteOut.model_validate(item)


@router.get("/clinical-documents/counter-referral-notes/{item_id}/pdf")
async def get_counter_referral_note_pdf(
    item_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("documents.read")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    pdf_bytes = await service.get_counter_referral_note_pdf(
        db, storage, clinic_id=clinic_id, item_id=item_id, actor_id=actor.id
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="contrarreferencia-{item_id}.pdf"'},
    )


@router.post(
    "/clinical-documents/counter-referral-notes/{item_id}/annul",
    response_model=CounterReferralNoteOut,
)
async def annul_counter_referral_note(
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("documents.write")),
    db: AsyncSession = Depends(get_db),
) -> CounterReferralNoteOut:
    item = await service.annul_counter_referral_note(
        db, clinic_id=clinic_id, item_id=item_id, data=payload, actor_id=actor.id
    )
    return CounterReferralNoteOut.model_validate(item)
