import io
import re
import uuid
from datetime import date

from PIL import Image
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.audit import service as audit_service
from app.core.errors import AppError
from app.core.storage import StorageBackend
from app.modules.iam.models import Clinic
from app.modules.patients import rules
from app.modules.patients.models import Patient, PatientContact
from app.modules.patients.schemas import (
    ContactCreateRequest,
    ContactUpdateRequest,
    DuplicateCheckRequest,
    PatientCreateRequest,
    PatientUpdateRequest,
)

MAX_PHOTO_BYTES = 2_000_000
ALLOWED_PHOTO_TYPES = {"image/png": ".png", "image/jpeg": ".jpg"}
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _unaccent_lower(
    value: ColumnElement[str] | InstrumentedAttribute[str] | str,
) -> ColumnElement[str]:
    return func.immutable_unaccent(func.lower(value))


async def _next_expediente_number(db: AsyncSession, clinic_id: uuid.UUID) -> str:
    stmt = select(Clinic).where(Clinic.id == clinic_id).with_for_update()
    clinic = (await db.execute(stmt)).scalar_one()
    number = clinic.next_patient_number
    clinic.next_patient_number = number + 1
    return f"{number:06d}"


async def create_patient(
    db: AsyncSession, *, clinic_id: uuid.UUID, data: PatientCreateRequest, actor_id: uuid.UUID
) -> Patient:
    expediente_number = await _next_expediente_number(db, clinic_id)
    full_name = rules.build_full_name(
        data.first_name, data.last_name_paternal, data.last_name_maternal
    )

    patient = Patient(
        clinic_id=clinic_id,
        expediente_number=expediente_number,
        first_name=data.first_name,
        last_name_paternal=data.last_name_paternal,
        last_name_maternal=data.last_name_maternal,
        full_name=full_name,
        date_of_birth=data.date_of_birth,
        sex=data.sex,
        phone=data.phone,
        email=data.email,
        address=data.address,
        created_by=actor_id,
    )
    db.add(patient)
    await db.flush()

    await audit_service.log(
        db,
        action="patients.created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="patient",
        entity_id=str(patient.id),
    )
    await db.commit()
    return patient


async def get_patient(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID, actor_id: uuid.UUID
) -> Patient:
    patient = await _get_patient_or_404(db, clinic_id=clinic_id, patient_id=patient_id)

    # CLAUDE.md sec. 5: se audita la lectura de expedientes.
    await audit_service.log(
        db,
        action="patients.read",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="patient",
        entity_id=str(patient.id),
    )
    await db.commit()
    return patient


async def get_patient_summary(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID, actor_id: uuid.UUID
) -> Patient:
    return await get_patient(db, clinic_id=clinic_id, patient_id=patient_id, actor_id=actor_id)


async def _get_patient_or_404(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> Patient:
    patient = await db.get(Patient, patient_id)
    if patient is None or patient.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Paciente no encontrado", status_code=404)
    return patient


async def list_patients(
    db: AsyncSession, *, clinic_id: uuid.UUID, status: str | None, limit: int, offset: int
) -> list[Patient]:
    stmt = select(Patient).where(Patient.clinic_id == clinic_id)
    if status:
        stmt = stmt.where(Patient.status == status)
    stmt = stmt.order_by(Patient.full_name).limit(limit).offset(offset)
    return list((await db.execute(stmt)).scalars().all())


async def search_patients(
    db: AsyncSession, *, clinic_id: uuid.UUID, query: str, limit: int = 20
) -> list[Patient]:
    q = query.strip()
    if not q:
        return []

    base = select(Patient).where(Patient.clinic_id == clinic_id)

    if _DATE_PATTERN.match(q):
        stmt = base.where(Patient.date_of_birth == date.fromisoformat(q))
        return list((await db.execute(stmt)).scalars().all())

    similarity = func.similarity(_unaccent_lower(Patient.full_name), _unaccent_lower(q))
    stmt = (
        base.where(
            (similarity > rules.DUPLICATE_NAME_SIMILARITY_THRESHOLD)
            | Patient.phone.ilike(f"%{q}%")
            | Patient.email.ilike(f"%{q}%")
            | Patient.expediente_number.ilike(f"%{q}%")
        )
        .order_by(similarity.desc())
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())


async def check_duplicates(
    db: AsyncSession, *, clinic_id: uuid.UUID, data: DuplicateCheckRequest
) -> list[tuple[Patient, float]]:
    full_name = rules.build_full_name(
        data.first_name, data.last_name_paternal, data.last_name_maternal
    )
    similarity = func.similarity(_unaccent_lower(Patient.full_name), _unaccent_lower(full_name))

    identity_conditions = []
    if data.date_of_birth is not None:
        identity_conditions.append(Patient.date_of_birth == data.date_of_birth)
    if data.phone:
        identity_conditions.append(Patient.phone == data.phone)

    if not identity_conditions:
        # Sin fecha de nacimiento ni telefono no hay forma confiable de confirmar duplicados.
        return []
    identity_match = or_(*identity_conditions)

    stmt = (
        select(Patient, similarity.label("score"))
        .where(
            Patient.clinic_id == clinic_id,
            similarity > rules.DUPLICATE_NAME_SIMILARITY_THRESHOLD,
            identity_match,
        )
        .order_by(similarity.desc())
        .limit(5)
    )
    rows = (await db.execute(stmt)).all()
    return [(patient, float(score)) for patient, score in rows]


async def update_patient(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: PatientUpdateRequest,
    actor_id: uuid.UUID,
) -> Patient:
    patient = await _get_patient_or_404(db, clinic_id=clinic_id, patient_id=patient_id)

    before = {"status": patient.status}
    changes: dict[str, object] = {}

    for field in ("first_name", "last_name_paternal", "last_name_maternal", "sex", "address"):
        value = getattr(data, field)
        if value is not None:
            setattr(patient, field, value)
            changes[field] = value

    if data.phone is not None:
        patient.phone = data.phone
        changes["phone"] = data.phone
    if data.email is not None:
        patient.email = data.email
        changes["email"] = data.email

    if any(f in changes for f in ("first_name", "last_name_paternal", "last_name_maternal")):
        patient.full_name = rules.build_full_name(
            patient.first_name, patient.last_name_paternal, patient.last_name_maternal
        )

    if data.status is not None and data.status != patient.status:
        changes["status"] = {
            "from": before["status"],
            "to": data.status,
            "reason": data.status_reason,
        }
        patient.status = data.status

    await audit_service.log(
        db,
        action="patients.updated",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="patient",
        entity_id=str(patient.id),
        details=changes if changes else None,
    )
    await db.commit()
    return patient


async def list_contacts(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[PatientContact]:
    await _get_patient_or_404(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = select(PatientContact).where(PatientContact.patient_id == patient_id)
    return list((await db.execute(stmt)).scalars().all())


async def create_contact(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: ContactCreateRequest,
    actor_id: uuid.UUID,
) -> PatientContact:
    await _get_patient_or_404(db, clinic_id=clinic_id, patient_id=patient_id)

    contact = PatientContact(
        patient_id=patient_id,
        role=data.role,
        full_name=data.full_name,
        relationship_label=data.relationship_label,
        phone=data.phone,
        email=data.email,
        created_by=actor_id,
    )
    db.add(contact)
    await audit_service.log(
        db,
        action="patients.contact_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="patient",
        entity_id=str(patient_id),
        details={"role": data.role},
    )
    await db.commit()
    return contact


async def update_contact(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    contact_id: uuid.UUID,
    data: ContactUpdateRequest,
    actor_id: uuid.UUID,
) -> PatientContact:
    await _get_patient_or_404(db, clinic_id=clinic_id, patient_id=patient_id)
    contact = await db.get(PatientContact, contact_id)
    if contact is None or contact.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Contacto no encontrado", status_code=404)

    for field in ("full_name", "relationship_label", "phone", "email"):
        value = getattr(data, field)
        if value is not None:
            setattr(contact, field, value)

    await audit_service.log(
        db,
        action="patients.contact_updated",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="patient",
        entity_id=str(patient_id),
    )
    await db.commit()
    return contact


async def delete_contact(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    contact_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> None:
    await _get_patient_or_404(db, clinic_id=clinic_id, patient_id=patient_id)
    contact = await db.get(PatientContact, contact_id)
    if contact is None or contact.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Contacto no encontrado", status_code=404)

    await db.delete(contact)
    await audit_service.log(
        db,
        action="patients.contact_deleted",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="patient",
        entity_id=str(patient_id),
    )
    await db.commit()


async def upload_photo(
    db: AsyncSession,
    storage: StorageBackend,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    content_type: str,
    data: bytes,
    actor_id: uuid.UUID,
) -> Patient:
    patient = await _get_patient_or_404(db, clinic_id=clinic_id, patient_id=patient_id)

    if len(data) > MAX_PHOTO_BYTES:
        raise AppError("FILE_TOO_LARGE", "La foto no puede pesar mas de 2 MB", status_code=400)
    suffix = ALLOWED_PHOTO_TYPES.get(content_type)
    if suffix is None:
        raise AppError("INVALID_FILE_TYPE", "La foto debe ser PNG o JPG", status_code=400)
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except Exception as exc:
        raise AppError(
            "INVALID_IMAGE", "El archivo no es una imagen valida", status_code=400
        ) from exc

    old_photo = patient.photo_path
    patient.photo_path = storage.save(data, subdir=f"patients/{patient_id}", suffix=suffix)

    await audit_service.log(
        db,
        action="patients.photo_updated",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="patient",
        entity_id=str(patient_id),
    )
    await db.commit()

    if old_photo:
        storage.delete(old_photo)
    return patient


async def read_photo(
    db: AsyncSession, storage: StorageBackend, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> tuple[bytes, str] | None:
    patient = await _get_patient_or_404(db, clinic_id=clinic_id, patient_id=patient_id)
    if not patient.photo_path:
        return None
    content_type = "image/jpeg" if patient.photo_path.endswith(".jpg") else "image/png"
    return storage.read(patient.photo_path), content_type
