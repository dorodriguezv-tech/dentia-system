import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.db import get_db
from app.core.deps import (
    get_clinic_id,
    get_current_user,
    require_permission,
    user_has_any_permission,
)
from app.core.errors import AppError
from app.modules.catalogs import service
from app.modules.catalogs.rules import CATALOG_TYPES
from app.modules.catalogs.schemas import (
    CatalogImportSummary,
    CatalogItemCreateRequest,
    CatalogItemOut,
    CatalogItemUpdateRequest,
)
from app.modules.iam.models import User

router = APIRouter(prefix="/catalogs", tags=["catalogs"])

# Quien ya puede leer/escribir en la pantalla original de cada catalogo (agenda,
# odontograma, diagnosticos, expediente) tambien puede leerlo aqui -- mas
# `catalogs.manage`, para que admin_clinica pueda ver y administrar catalogos
# clinicos sin tener esos permisos clinicos (CLAUDE.md sec. 5: el superadmin
# tampoco los tiene, y a proposito no se le da `catalogs.manage`).
READ_PERMISSION_BY_TYPE: dict[str, str] = {
    "appointment_type": "agenda.read",
    "odontogram_finding": "odontogram.read",
    "diagnosis": "diagnosis.read",
    "history_category": "records.read",
    "condition_alert_keyword": "records.read",
    "medication_alert_keyword": "records.read",
    "family_relationship": "records.read",
    "family_condition": "records.read",
    "pathological_condition": "records.read",
    "systems_review_finding": "records.read",
    "skull_type": "records.read",
    "facial_biotype": "records.read",
    "periodontal_anamnesis_question": "records.read",
    "pediatric_character": "records.read",
    "terminal_plane": "records.read",
    "pediatric_tooth_anomaly": "records.read",
}


def _check_catalog_type_param(catalog_type: str) -> None:
    if catalog_type not in CATALOG_TYPES:
        raise AppError("INVALID_CATALOG_TYPE", "Tipo de catalogo desconocido", status_code=400)


@router.get("/{catalog_type}", response_model=list[CatalogItemOut])
async def list_catalog_items(
    catalog_type: str,
    include_inactive: bool = Query(default=False),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CatalogItemOut]:
    _check_catalog_type_param(catalog_type)
    allowed = await user_has_any_permission(
        db,
        user_id=current_user.id,
        clinic_id=clinic_id,
        codes=(READ_PERMISSION_BY_TYPE[catalog_type], "catalogs.manage"),
    )
    if not allowed:
        raise AppError("FORBIDDEN", "No tienes permiso para esta accion", status_code=403)
    # Solo quien administra catalogos puede pedir los inactivos (la pantalla de
    # catalogos los muestra tachados; cualquier otro selector solo ve los activos).
    if include_inactive:
        can_manage = await user_has_any_permission(
            db, user_id=current_user.id, clinic_id=clinic_id, codes=("catalogs.manage",)
        )
        if not can_manage:
            include_inactive = False
    items = await service.list_items(
        db, clinic_id=clinic_id, catalog_type=catalog_type, include_inactive=include_inactive
    )
    return [CatalogItemOut.model_validate(i) for i in items]


@router.post("/{catalog_type}", response_model=CatalogItemOut, status_code=201)
async def create_catalog_item(
    catalog_type: str,
    payload: CatalogItemCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("catalogs.manage")),
    db: AsyncSession = Depends(get_db),
) -> CatalogItemOut:
    _check_catalog_type_param(catalog_type)
    item = await service.create_item(
        db, clinic_id=clinic_id, catalog_type=catalog_type, data=payload, actor_id=actor.id
    )
    return CatalogItemOut.model_validate(item)


def _csv_response(content: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{catalog_type}/export")
async def export_catalog_items(
    catalog_type: str,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("catalogs.manage")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    _check_catalog_type_param(catalog_type)
    content = await service.export_csv(db, clinic_id=clinic_id, catalog_type=catalog_type)
    return _csv_response(content, f"{catalog_type}.csv")


@router.post("/{catalog_type}/import", response_model=CatalogImportSummary)
async def import_catalog_items(
    catalog_type: str,
    file: UploadFile = File(...),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("catalogs.manage")),
    db: AsyncSession = Depends(get_db),
) -> CatalogImportSummary:
    _check_catalog_type_param(catalog_type)
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AppError(
            "INVALID_CSV", "El archivo no es un CSV de texto valido (UTF-8)", status_code=400
        ) from exc
    return await service.import_csv(
        db, clinic_id=clinic_id, catalog_type=catalog_type, csv_text=text, actor_id=actor.id
    )


@router.patch("/{catalog_type}/{item_id}", response_model=CatalogItemOut)
async def update_catalog_item(
    catalog_type: str,
    item_id: uuid.UUID,
    payload: CatalogItemUpdateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("catalogs.manage")),
    db: AsyncSession = Depends(get_db),
) -> CatalogItemOut:
    _check_catalog_type_param(catalog_type)
    item = await service.update_item(
        db,
        clinic_id=clinic_id,
        catalog_type=catalog_type,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return CatalogItemOut.model_validate(item)
