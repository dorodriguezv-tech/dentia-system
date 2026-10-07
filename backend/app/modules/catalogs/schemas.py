import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CatalogItemOut(BaseModel):
    id: uuid.UUID
    catalog_type: str
    code: str
    name: str
    is_active: bool
    sort_order: int
    extra: dict[str, Any]
    updated_at: datetime

    model_config = {"from_attributes": True}


class CatalogItemCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=60, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1, max_length=200)
    sort_order: int = 0
    extra: dict[str, Any] = Field(default_factory=dict)


class CatalogItemUpdateRequest(BaseModel):
    """`code` y `catalog_type` nunca se editan (regla del modulo, ver rules.py):
    los usan la IA y los reportes. Solo lo visible/administrativo cambia."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    is_active: bool | None = None
    sort_order: int | None = None
    extra: dict[str, Any] | None = None


class CatalogImportSummary(BaseModel):
    """Resultado de importar un CSV (Fase 12.2, Parte B, pendiente de B1): cada fila
    mala se reporta en `errors` y se salta -- una fila invalida no aborta el resto
    del archivo."""

    created: int
    updated: int
    errors: list[str]
