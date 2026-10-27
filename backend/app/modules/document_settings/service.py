"""Servicio de "Formatos de documentos" (Fase A del rediseno del expediente,
docs/clinica): logos izquierdo/derecho, titulo institucional y lugar usados en
el encabezado de todo PDF (ver app/modules/documents/pdf_header.py).

Sigue el mismo patron que app/modules/branding/service.py (subida/validacion de
imagen con Pillow + svg_sanitize), pero sin el atajo de "una sola clinica
visible" de branding: aqui siempre se opera sobre el `clinic_id` de la
sucursal autenticada (X-Clinic-Id), como el resto de los modulos clinicos.
"""

import io
import uuid

from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import AppError
from app.core.storage import StorageBackend
from app.modules.branding.svg_sanitize import InvalidSvgError, sanitize_svg
from app.modules.document_settings.models import ClinicDocumentSettings
from app.modules.document_settings.schemas import (
    DocumentSettingsOut,
    DocumentSettingsUpdateRequest,
)

MAX_LOGO_BYTES = 1_000_000
ALLOWED_LOGO_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/svg+xml": ".svg",
}

_LOGO_LEFT_URL = "/api/v1/document-settings/logo-left"
_LOGO_RIGHT_URL = "/api/v1/document-settings/logo-right"


async def _get_or_create(db: AsyncSession, clinic_id: uuid.UUID) -> ClinicDocumentSettings:
    settings = await db.get(ClinicDocumentSettings, clinic_id)
    if settings is None:
        settings = ClinicDocumentSettings(clinic_id=clinic_id)
        db.add(settings)
        await db.flush()
    return settings


def _settings_out(settings: ClinicDocumentSettings) -> DocumentSettingsOut:
    return DocumentSettingsOut(
        institutional_title=settings.institutional_title,
        place_label=settings.place_label,
        logo_left_url=_LOGO_LEFT_URL if settings.logo_left_path else None,
        logo_right_url=_LOGO_RIGHT_URL if settings.logo_right_path else None,
        has_logo_left=settings.logo_left_path is not None,
        has_logo_right=settings.logo_right_path is not None,
    )


async def get_document_settings(db: AsyncSession, *, clinic_id: uuid.UUID) -> DocumentSettingsOut:
    settings = await db.get(ClinicDocumentSettings, clinic_id)
    if settings is None:
        return DocumentSettingsOut(
            institutional_title=None,
            place_label=None,
            logo_left_url=None,
            logo_right_url=None,
            has_logo_left=False,
            has_logo_right=False,
        )
    return _settings_out(settings)


async def update_document_settings(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    data: DocumentSettingsUpdateRequest,
    actor_id: uuid.UUID,
) -> DocumentSettingsOut:
    settings = await _get_or_create(db, clinic_id)
    settings.institutional_title = data.institutional_title
    settings.place_label = data.place_label
    settings.updated_by = actor_id

    await audit_service.log(
        db,
        action="document_settings.updated",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="clinic_document_settings",
        entity_id=str(clinic_id),
    )
    await db.commit()
    return _settings_out(settings)


def _validate_logo_bytes(content_type: str, data: bytes) -> bytes:
    if len(data) > MAX_LOGO_BYTES:
        raise AppError("FILE_TOO_LARGE", "El logo no puede pesar mas de 1 MB", status_code=400)

    suffix = ALLOWED_LOGO_TYPES.get(content_type)
    if suffix is None:
        raise AppError("INVALID_FILE_TYPE", "El logo debe ser PNG, JPG o SVG", status_code=400)

    if content_type == "image/svg+xml":
        try:
            return sanitize_svg(data)
        except InvalidSvgError as exc:
            raise AppError("INVALID_SVG", str(exc), status_code=400) from exc

    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except Exception as exc:
        raise AppError(
            "INVALID_IMAGE", "El archivo no es una imagen valida", status_code=400
        ) from exc
    return data


async def upload_logo(
    db: AsyncSession,
    storage: StorageBackend,
    *,
    clinic_id: uuid.UUID,
    side: str,
    content_type: str,
    data: bytes,
    actor_id: uuid.UUID,
) -> DocumentSettingsOut:
    assert side in ("left", "right")
    data = _validate_logo_bytes(content_type, data)
    suffix = ALLOWED_LOGO_TYPES[content_type]

    settings = await _get_or_create(db, clinic_id)
    key = storage.save(data, subdir=f"document_settings/{clinic_id}", suffix=suffix)

    old_key = settings.logo_left_path if side == "left" else settings.logo_right_path
    if side == "left":
        settings.logo_left_path = key
    else:
        settings.logo_right_path = key
    settings.updated_by = actor_id

    await audit_service.log(
        db,
        action="document_settings.logo_updated",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="clinic_document_settings",
        entity_id=str(clinic_id),
        details={"side": side},
    )
    await db.commit()

    if old_key:
        storage.delete(old_key)

    return _settings_out(settings)


async def read_logo(
    db: AsyncSession, storage: StorageBackend, *, clinic_id: uuid.UUID, side: str
) -> tuple[bytes, str] | None:
    """A diferencia de branding, aqui no hay un logo de DENT-IA de respaldo: si
    la sucursal no subio nada, regresa None -- quien construye el encabezado
    del PDF (pdf_header.py) decide el reemplazo (hoy: el logo unico de
    branding como logo izquierdo, para no romper los PDF existentes)."""
    assert side in ("left", "right")
    settings = await db.get(ClinicDocumentSettings, clinic_id)
    key = None
    if settings is not None:
        key = settings.logo_left_path if side == "left" else settings.logo_right_path
    if key is None:
        return None
    return storage.read(key), _guess_content_type(key)


def _guess_content_type(key: str) -> str:
    if key.endswith(".svg"):
        return "image/svg+xml"
    if key.endswith(".jpg") or key.endswith(".jpeg"):
        return "image/jpeg"
    return "image/png"
