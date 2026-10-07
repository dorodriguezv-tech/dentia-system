import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import AuditedMixin, Base


class ClinicCatalogItem(AuditedMixin, Base):
    """Un elemento de un catalogo administrable por sucursal (Fase 12.2, Parte B1).

    `code` es el identificador interno inmutable (lo usan la IA y los reportes);
    `name` es la etiqueta visible, editable. Nunca se borra un elemento (puede estar
    referenciado por registros clinicos historicos): se desactiva con `is_active`.
    """

    __tablename__ = "clinic_catalog_items"
    __table_args__ = (
        UniqueConstraint("clinic_id", "catalog_type", "code", name="uq_catalog_item_code"),
    )

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), index=True
    )
    catalog_type: Mapped[str] = mapped_column(String(40), index=True)
    code: Mapped[str] = mapped_column(String(60))
    name: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    extra: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
