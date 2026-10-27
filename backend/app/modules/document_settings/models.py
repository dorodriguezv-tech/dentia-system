import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ClinicDocumentSettings(Base):
    """ "Formatos de documentos" (Fase A del rediseno del expediente,
    docs/clinica): un unico par de logos (izquierdo/derecho), titulo
    institucional y lugar, usados en el encabezado de TODO documento imprimible
    (historias, recetas, consentimientos, presupuesto, referencia, ficha de
    tratamientos, etc. -- ver app/modules/documents/pdf_header.py).

    Una fila por sucursal (mismo patron que ClinicBranding, clinic_id es la PK).
    Decision tecnica (no hay tabla en el plan todavia): se deja separada de
    ClinicBranding porque conceptualmente es otra cosa (encabezado impreso vs.
    identidad visual de la app) y porque CLAUDE.md pide una tabla nueva
    `clinic_document_settings` explicitamente.
    """

    __tablename__ = "clinic_document_settings"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE"), primary_key=True
    )
    logo_left_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_right_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    institutional_title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    place_label: Mapped[str | None] = mapped_column(String(150), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
