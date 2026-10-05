import io
import uuid
from datetime import UTC, datetime

from PIL import Image as PILImage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import AppError
from app.core.storage import StorageBackend
from app.modules.encounters.models import Encounter
from app.modules.imaging import rules
from app.modules.imaging.models import Image
from app.modules.odontogram import rules as odontogram_rules
from app.modules.patients.models import Patient
from app.modules.treatment.models import ProcedurePerformed, ProcedurePlanned


class UploadedFile:
    def __init__(self, *, filename: str, content_type: str, data: bytes) -> None:
        self.filename = filename
        self.content_type = content_type
        self.data = data


async def _get_patient_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> Patient:
    patient = await db.get(Patient, patient_id)
    if patient is None or patient.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Paciente no encontrado", status_code=404)
    return patient


async def _get_encounter_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, encounter_id: uuid.UUID
) -> Encounter:
    encounter = await db.get(Encounter, encounter_id)
    if encounter is None or encounter.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Atencion no encontrada", status_code=404)
    return encounter


def _make_thumbnail(data: bytes) -> bytes:
    with PILImage.open(io.BytesIO(data)) as image:
        image = image.convert("RGB")
        image.thumbnail(rules.THUMBNAIL_SIZE)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()


async def upload_images(
    db: AsyncSession,
    storage: StorageBackend,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    encounter_id: uuid.UUID,
    study_type: str,
    tooth_fdi: int | None,
    procedure_planned_id: uuid.UUID | None,
    procedure_performed_id: uuid.UUID | None,
    notes: str | None,
    files: list[UploadedFile],
    actor_id: uuid.UUID,
) -> list[Image]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    encounter = await _get_encounter_in_clinic(db, clinic_id=clinic_id, encounter_id=encounter_id)
    if encounter.patient_id != patient_id:
        raise AppError(
            "ENCOUNTER_PATIENT_MISMATCH",
            "La atencion no pertenece a este paciente",
            status_code=400,
        )
    if tooth_fdi is not None and not odontogram_rules.is_valid_tooth(tooth_fdi):
        raise AppError("INVALID_TOOTH", f"Pieza FDI invalida: {tooth_fdi}", status_code=422)
    if procedure_planned_id is not None:
        planned = await db.get(ProcedurePlanned, procedure_planned_id)
        if planned is None or planned.clinic_id != clinic_id or planned.patient_id != patient_id:
            raise AppError("NOT_FOUND", "Procedimiento planificado no encontrado", status_code=404)
    if procedure_performed_id is not None:
        performed = await db.get(ProcedurePerformed, procedure_performed_id)
        if (
            performed is None
            or performed.clinic_id != clinic_id
            or performed.patient_id != patient_id
        ):
            raise AppError("NOT_FOUND", "Procedimiento realizado no encontrado", status_code=404)
    if not files:
        raise AppError("VALIDATION_ERROR", "Se necesita al menos un archivo", status_code=422)

    created: list[Image] = []
    for file in files:
        suffix = rules.ALLOWED_CONTENT_TYPES.get(file.content_type)
        if suffix is None:
            raise AppError("INVALID_FILE_TYPE", "Solo se aceptan JPG, PNG o PDF", status_code=400)
        if len(file.data) > rules.MAX_IMAGE_BYTES:
            raise AppError(
                "FILE_TOO_LARGE", "Cada archivo no puede pesar mas de 15 MB", status_code=400
            )

        thumbnail_path = None
        if file.content_type in ("image/jpeg", "image/png"):
            try:
                with PILImage.open(io.BytesIO(file.data)) as image:
                    image.verify()
            except Exception as exc:
                raise AppError(
                    "INVALID_IMAGE", f"'{file.filename}' no es una imagen valida", status_code=400
                ) from exc
            thumbnail_bytes = _make_thumbnail(file.data)
            thumbnail_path = storage.save(
                thumbnail_bytes,
                subdir=f"imaging/{clinic_id}/{patient_id}/thumbnails",
                suffix=".jpg",
            )

        file_path = storage.save(
            file.data, subdir=f"imaging/{clinic_id}/{patient_id}", suffix=suffix
        )

        item = Image(
            clinic_id=clinic_id,
            patient_id=patient_id,
            encounter_id=encounter_id,
            study_type=study_type,
            tooth_fdi=tooth_fdi,
            procedure_planned_id=procedure_planned_id,
            procedure_performed_id=procedure_performed_id,
            file_path=file_path,
            thumbnail_path=thumbnail_path,
            content_type=file.content_type,
            original_filename=file.filename,
            notes=notes,
            created_by=actor_id,
        )
        db.add(item)
        await db.flush()
        created.append(item)

        await audit_service.log(
            db,
            action="imaging.image_uploaded",
            actor_user_id=actor_id,
            clinic_id=clinic_id,
            entity_type="image",
            entity_id=str(item.id),
            details={"patient_id": str(patient_id), "study_type": study_type},
        )

    await db.commit()
    return created


async def list_images(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    study_type: str | None = None,
    tooth_fdi: int | None = None,
) -> list[Image]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = select(Image).where(Image.clinic_id == clinic_id, Image.patient_id == patient_id)
    if study_type is not None:
        stmt = stmt.where(Image.study_type == study_type)
    if tooth_fdi is not None:
        stmt = stmt.where(Image.tooth_fdi == tooth_fdi)
    stmt = stmt.order_by(Image.created_at.desc())
    return list((await db.execute(stmt)).scalars().all())


async def _get_image_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, image_id: uuid.UUID
) -> Image:
    image = await db.get(Image, image_id)
    if image is None or image.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Imagen no encontrada", status_code=404)
    return image


async def read_image(
    db: AsyncSession,
    storage: StorageBackend,
    *,
    clinic_id: uuid.UUID,
    image_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> tuple[bytes, str]:
    image = await _get_image_in_clinic(db, clinic_id=clinic_id, image_id=image_id)
    await audit_service.log(
        db,
        action="imaging.image_viewed",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="image",
        entity_id=str(image.id),
    )
    await db.commit()
    return storage.read(image.file_path), image.content_type


async def read_thumbnail(
    db: AsyncSession, storage: StorageBackend, *, clinic_id: uuid.UUID, image_id: uuid.UUID
) -> bytes | None:
    image = await _get_image_in_clinic(db, clinic_id=clinic_id, image_id=image_id)
    if image.thumbnail_path is None:
        return None
    return storage.read(image.thumbnail_path)


async def annul_image(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    image_id: uuid.UUID,
    reason: str,
    actor_id: uuid.UUID,
) -> Image:
    image = await _get_image_in_clinic(db, clinic_id=clinic_id, image_id=image_id)
    image.is_active = False
    image.annul_reason = reason
    image.annulled_by = actor_id
    image.annulled_at = datetime.now(UTC)

    await audit_service.log(
        db,
        action="imaging.image_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="image",
        entity_id=str(image_id),
        details={"reason": reason},
    )
    await db.commit()
    return image
