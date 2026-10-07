import csv
import io
import json
import re
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import AppError
from app.modules.catalogs import rules
from app.modules.catalogs.models import ClinicCatalogItem
from app.modules.catalogs.schemas import (
    CatalogImportSummary,
    CatalogItemCreateRequest,
    CatalogItemUpdateRequest,
)

_CODE_PATTERN = re.compile(r"^[a-z0-9_]+$")
_TRUE_VALUES = {"true", "1", "si", "sí"}


def _check_catalog_type(catalog_type: str) -> None:
    if not rules.is_valid_catalog_type(catalog_type):
        raise AppError("INVALID_CATALOG_TYPE", "Tipo de catalogo desconocido", status_code=400)


async def list_items(
    db: AsyncSession, *, clinic_id: uuid.UUID, catalog_type: str, include_inactive: bool = False
) -> list[ClinicCatalogItem]:
    """Lectura del catalogo -- reemplaza las constantes fijas que usaban agenda,
    odontogram, diagnosis y records (Fase 12.2, Parte B1). Sin cache propia: la
    tabla es pequena (decenas de filas por sucursal) y ya tiene indice por
    (clinic_id, catalog_type), asi que una consulta directa es tan rapida como
    cualquier cache en este tamano -- si la clinica crece mucho mas, ahi si vale la
    pena agregar una capa de cache real.
    """
    _check_catalog_type(catalog_type)
    stmt = (
        select(ClinicCatalogItem)
        .where(
            ClinicCatalogItem.clinic_id == clinic_id,
            ClinicCatalogItem.catalog_type == catalog_type,
        )
        .order_by(ClinicCatalogItem.sort_order, ClinicCatalogItem.name)
    )
    if not include_inactive:
        stmt = stmt.where(ClinicCatalogItem.is_active.is_(True))
    return list((await db.execute(stmt)).scalars().all())


async def get_active_codes(
    db: AsyncSession, *, clinic_id: uuid.UUID, catalog_type: str
) -> set[str]:
    """Para validar un codigo entrante (p.ej. `appointment_type`, `finding_code`)
    contra los elementos activos del catalogo, en vez de una tupla fija en codigo."""
    items = await list_items(db, clinic_id=clinic_id, catalog_type=catalog_type)
    return {item.code for item in items}


async def create_item(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    catalog_type: str,
    data: CatalogItemCreateRequest,
    actor_id: uuid.UUID,
) -> ClinicCatalogItem:
    _check_catalog_type(catalog_type)
    item = ClinicCatalogItem(
        clinic_id=clinic_id,
        catalog_type=catalog_type,
        code=data.code,
        name=data.name,
        sort_order=data.sort_order,
        extra=data.extra,
        created_by=actor_id,
    )
    db.add(item)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise AppError(
            "CODE_TAKEN", "Ya existe un elemento con ese codigo en este catalogo", status_code=409
        ) from exc

    await audit_service.log(
        db,
        action="catalogs.item_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="clinic_catalog_item",
        entity_id=str(item.id),
        details={"catalog_type": catalog_type, "code": data.code},
    )
    await db.commit()
    return item


async def _get_item_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, catalog_type: str, item_id: uuid.UUID
) -> ClinicCatalogItem:
    item = await db.get(ClinicCatalogItem, item_id)
    if item is None or item.clinic_id != clinic_id or item.catalog_type != catalog_type:
        raise AppError("NOT_FOUND", "Elemento de catalogo no encontrado", status_code=404)
    return item


async def update_item(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    catalog_type: str,
    item_id: uuid.UUID,
    data: CatalogItemUpdateRequest,
    actor_id: uuid.UUID,
) -> ClinicCatalogItem:
    _check_catalog_type(catalog_type)
    item = await _get_item_in_clinic(
        db, clinic_id=clinic_id, catalog_type=catalog_type, item_id=item_id
    )

    if data.name is not None:
        item.name = data.name
    if data.is_active is not None:
        item.is_active = data.is_active
    if data.sort_order is not None:
        item.sort_order = data.sort_order
    if data.extra is not None:
        item.extra = data.extra

    await audit_service.log(
        db,
        action="catalogs.item_updated",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="clinic_catalog_item",
        entity_id=str(item.id),
        details={"catalog_type": catalog_type},
    )
    await db.commit()
    return item


async def export_csv(db: AsyncSession, *, clinic_id: uuid.UUID, catalog_type: str) -> str:
    """CSV de ida y vuelta con `import_csv`: incluye los inactivos (quien exporta ya
    tiene `catalogs.manage`, ver router.py) para que editar y reimportar no los
    reactive sin querer."""
    _check_catalog_type(catalog_type)
    items = await list_items(
        db, clinic_id=clinic_id, catalog_type=catalog_type, include_inactive=True
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["code", "name", "is_active", "sort_order", "extra"])
    for item in items:
        writer.writerow(
            [item.code, item.name, item.is_active, item.sort_order, json.dumps(item.extra)]
        )
    return buffer.getvalue()


async def import_csv(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    catalog_type: str,
    csv_text: str,
    actor_id: uuid.UUID,
) -> CatalogImportSummary:
    """Importa por `code`: si ya existe en esta sucursal y este catalogo, actualiza
    nombre/activo/orden/extra; si no, lo crea. Una fila invalida se reporta en
    `errors` y se salta -- no aborta el resto del archivo (import parcial, no todo
    o nada: quien importa revisa los errores y corrige solo esas filas)."""
    _check_catalog_type(catalog_type)
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None or not {"code", "name"}.issubset(set(reader.fieldnames)):
        raise AppError(
            "INVALID_CSV", "El CSV debe tener al menos las columnas 'code' y 'name'", 400
        )

    existing_by_code = {
        item.code: item
        for item in await list_items(
            db, clinic_id=clinic_id, catalog_type=catalog_type, include_inactive=True
        )
    }
    created = 0
    updated = 0
    errors: list[str] = []

    for row_number, row in enumerate(reader, start=2):  # fila 1 es el encabezado
        code = (row.get("code") or "").strip()
        name = (row.get("name") or "").strip()
        if not code or not _CODE_PATTERN.match(code):
            errors.append(f"Fila {row_number}: codigo invalido ('{code}')")
            continue
        if not name:
            errors.append(f"Fila {row_number}: nombre vacio (codigo '{code}')")
            continue

        extra_raw = (row.get("extra") or "").strip()
        try:
            extra = json.loads(extra_raw) if extra_raw else {}
            if not isinstance(extra, dict):
                raise ValueError("extra debe ser un objeto JSON")
        except (json.JSONDecodeError, ValueError):
            errors.append(f"Fila {row_number}: columna 'extra' no es JSON valido (codigo '{code}')")
            continue

        sort_order_raw = (row.get("sort_order") or "0").strip()
        try:
            sort_order = int(sort_order_raw)
        except ValueError:
            errors.append(f"Fila {row_number}: 'sort_order' no es un numero (codigo '{code}')")
            continue

        is_active = (row.get("is_active") or "true").strip().lower() in _TRUE_VALUES

        existing = existing_by_code.get(code)
        if existing is not None:
            existing.name = name
            existing.is_active = is_active
            existing.sort_order = sort_order
            existing.extra = extra
            updated += 1
        else:
            new_item = ClinicCatalogItem(
                clinic_id=clinic_id,
                catalog_type=catalog_type,
                code=code,
                name=name,
                is_active=is_active,
                sort_order=sort_order,
                extra=extra,
                created_by=actor_id,
            )
            db.add(new_item)
            existing_by_code[code] = new_item
            created += 1

    await audit_service.log(
        db,
        action="catalogs.imported",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="clinic_catalog_item",
        entity_id=catalog_type,
        details={
            "catalog_type": catalog_type,
            "created": created,
            "updated": updated,
            "errors": len(errors),
        },
    )
    await db.commit()
    return CatalogImportSummary(created=created, updated=updated, errors=errors)
