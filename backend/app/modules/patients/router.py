import uuid

from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.core.errors import AppError
from app.core.storage import StorageBackend, get_storage_backend
from app.modules.agenda import service as agenda_service
from app.modules.iam.models import User
from app.modules.patients import service
from app.modules.patients.models import Patient
from app.modules.patients.rules import calculate_age
from app.modules.patients.schemas import (
    ContactCreateRequest,
    ContactOut,
    ContactUpdateRequest,
    DuplicateCandidateOut,
    DuplicateCheckRequest,
    PatientCreateRequest,
    PatientListItemOut,
    PatientOut,
    PatientSummaryOut,
    PatientUpdateRequest,
    StatusCode,
)
from app.modules.records import service as records_service

router = APIRouter(tags=["patients"])


def _patient_out(patient: Patient) -> PatientOut:
    return PatientOut(
        id=patient.id,
        expediente_number=patient.expediente_number,
        first_name=patient.first_name,
        last_name_paternal=patient.last_name_paternal,
        last_name_maternal=patient.last_name_maternal,
        full_name=patient.full_name,
        date_of_birth=patient.date_of_birth,
        sex=patient.sex,
        patient_type=patient.patient_type,
        phone=patient.phone,
        email=patient.email,
        address=patient.address,
        status=patient.status,
        has_photo=patient.photo_path is not None,
        default_resource_id=patient.default_resource_id,
        primary_provider_id=patient.primary_provider_id,
        birth_place=patient.birth_place,
        blood_type=patient.blood_type,
        education_level=patient.education_level,
        can_read_write=patient.can_read_write,
        religion=patient.religion,
        ethnic_group=patient.ethnic_group,
        race=patient.race,
        occupation=patient.occupation,
        marital_status=patient.marital_status,
    )


def _patient_list_item(patient: Patient) -> PatientListItemOut:
    return PatientListItemOut(
        id=patient.id,
        expediente_number=patient.expediente_number,
        full_name=patient.full_name,
        date_of_birth=patient.date_of_birth,
        status=patient.status,
        phone=patient.phone,
        default_resource_id=patient.default_resource_id,
        primary_provider_id=patient.primary_provider_id,
    )


async def _summary_out(db: AsyncSession, patient: Patient) -> PatientSummaryOut:
    alerts = await records_service.get_patient_alerts(
        db, clinic_id=patient.clinic_id, patient_id=patient.id
    )
    return PatientSummaryOut(
        id=patient.id,
        expediente_number=patient.expediente_number,
        full_name=patient.full_name,
        age=calculate_age(patient.date_of_birth),
        status=patient.status,
        has_photo=patient.photo_path is not None,
        alerts=alerts,
    )


@router.get("/patients", response_model=list[PatientListItemOut])
async def list_patients(
    status_filter: StatusCode | None = Query(default=None, alias="status"),
    mine_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("patients.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PatientListItemOut]:
    primary_provider_id: uuid.UUID | None = None
    if mine_only:
        # B3 (Parte B, Fase 12.2): "Mis pacientes" -- un odontologo/especialista sin
        # Provider en esta sucursal simplemente no tiene pacientes propios, no es un
        # error.
        provider = await agenda_service.get_provider_for_user(
            db, clinic_id=clinic_id, user_id=actor.id
        )
        if provider is None:
            return []
        primary_provider_id = provider.id

    patients = await service.list_patients(
        db,
        clinic_id=clinic_id,
        status=status_filter,
        limit=limit,
        offset=offset,
        primary_provider_id=primary_provider_id,
    )
    return [_patient_list_item(p) for p in patients]


@router.get("/patients/search", response_model=list[PatientListItemOut])
async def search_patients(
    q: str = Query(min_length=1),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("patients.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PatientListItemOut]:
    patients = await service.search_patients(db, clinic_id=clinic_id, query=q)
    return [_patient_list_item(p) for p in patients]


@router.post("/patients/duplicates-check", response_model=list[DuplicateCandidateOut])
async def duplicates_check(
    payload: DuplicateCheckRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("patients.read")),
    db: AsyncSession = Depends(get_db),
) -> list[DuplicateCandidateOut]:
    matches = await service.check_duplicates(db, clinic_id=clinic_id, data=payload)
    return [
        DuplicateCandidateOut(
            id=patient.id,
            expediente_number=patient.expediente_number,
            full_name=patient.full_name,
            date_of_birth=patient.date_of_birth,
            phone=patient.phone,
            similarity=round(score, 2),
        )
        for patient, score in matches
    ]


@router.post("/patients", response_model=PatientOut, status_code=201)
async def create_patient(
    payload: PatientCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("patients.write")),
    db: AsyncSession = Depends(get_db),
) -> PatientOut:
    patient = await service.create_patient(db, clinic_id=clinic_id, data=payload, actor_id=actor.id)
    return _patient_out(patient)


@router.get("/patients/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("patients.read")),
    db: AsyncSession = Depends(get_db),
) -> PatientOut:
    patient = await service.get_patient(
        db, clinic_id=clinic_id, patient_id=patient_id, actor_id=actor.id
    )
    return _patient_out(patient)


@router.get("/patients/{patient_id}/summary", response_model=PatientSummaryOut)
async def get_patient_summary(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("patients.read")),
    db: AsyncSession = Depends(get_db),
) -> PatientSummaryOut:
    patient = await service.get_patient_summary(
        db, clinic_id=clinic_id, patient_id=patient_id, actor_id=actor.id
    )
    return await _summary_out(db, patient)


@router.patch("/patients/{patient_id}", response_model=PatientOut)
async def update_patient(
    patient_id: uuid.UUID,
    payload: PatientUpdateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("patients.write")),
    db: AsyncSession = Depends(get_db),
) -> PatientOut:
    patient = await service.update_patient(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return _patient_out(patient)


@router.get("/patients/{patient_id}/contacts", response_model=list[ContactOut])
async def list_contacts(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("patients.read")),
    db: AsyncSession = Depends(get_db),
) -> list[ContactOut]:
    contacts = await service.list_contacts(db, clinic_id=clinic_id, patient_id=patient_id)
    return [ContactOut.model_validate(c) for c in contacts]


@router.post("/patients/{patient_id}/contacts", response_model=ContactOut, status_code=201)
async def create_contact(
    patient_id: uuid.UUID,
    payload: ContactCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("patients.write")),
    db: AsyncSession = Depends(get_db),
) -> ContactOut:
    contact = await service.create_contact(
        db, clinic_id=clinic_id, patient_id=patient_id, data=payload, actor_id=actor.id
    )
    return ContactOut.model_validate(contact)


@router.patch("/patients/{patient_id}/contacts/{contact_id}", response_model=ContactOut)
async def update_contact(
    patient_id: uuid.UUID,
    contact_id: uuid.UUID,
    payload: ContactUpdateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("patients.write")),
    db: AsyncSession = Depends(get_db),
) -> ContactOut:
    contact = await service.update_contact(
        db,
        clinic_id=clinic_id,
        patient_id=patient_id,
        contact_id=contact_id,
        data=payload,
        actor_id=actor.id,
    )
    return ContactOut.model_validate(contact)


@router.delete("/patients/{patient_id}/contacts/{contact_id}", status_code=204)
async def delete_contact(
    patient_id: uuid.UUID,
    contact_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("patients.write")),
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.delete_contact(
        db, clinic_id=clinic_id, patient_id=patient_id, contact_id=contact_id, actor_id=actor.id
    )


@router.post("/patients/{patient_id}/photo", response_model=PatientOut)
async def upload_photo(
    patient_id: uuid.UUID,
    file: UploadFile,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("patients.write")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> PatientOut:
    data = await file.read()
    patient = await service.upload_photo(
        db,
        storage,
        clinic_id=clinic_id,
        patient_id=patient_id,
        content_type=file.content_type or "application/octet-stream",
        data=data,
        actor_id=actor.id,
    )
    return _patient_out(patient)


@router.get("/patients/{patient_id}/photo")
async def get_photo(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("patients.read")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    asset = await service.read_photo(db, storage, clinic_id=clinic_id, patient_id=patient_id)
    if asset is None:
        raise AppError("NOT_FOUND", "El paciente no tiene foto", status_code=404)
    data, content_type = asset
    return Response(content=data, media_type=content_type)
