import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import AuditedMixin, Base


class _AnnullableMixin:
    """Regla 2 de CLAUDE.md: sin borrado fisico, se anula con motivo y queda auditado."""

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    annul_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    annulled_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    annulled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentTemplate(AuditedMixin, Base):
    """Plantilla de documento/consentimiento (regla 7 de CLAUDE.md: nunca se sobrescribe).
    Editarla crea una fila nueva con `version` incrementada y `supersedes_id` apuntando a
    la anterior -- mismo patron de evento que ToothFinding (Fase 5): is_current=False en
    la version vieja, nunca se le toca el contenido. Un Consent guarda el id exacto de la
    version que uso, no el codigo, para que un cambio de plantilla despues no altere
    retroactivamente lo que un paciente ya firmo."""

    __tablename__ = "document_templates"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(default=1)
    html_content: Mapped[str] = mapped_column(Text)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("document_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)


class Consent(_AnnullableMixin, AuditedMixin, Base):
    """Consentimiento firmado (docs/09 Fase 9). Se crea ya firmado -- no hay un estado
    "borrador": capturar la firma en pantalla y generar el PDF es un solo acto atomico.
    Despues de creado no se edita (solo se puede anular con motivo, regla 2); corregir un
    dato significa anular este y capturar uno nuevo, nunca sobrescribir el PDF ya firmado
    (regla 7)."""

    __tablename__ = "consents"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("document_templates.id", ondelete="RESTRICT")
    )
    # "ligado a procedimiento o plan" (docs/09): a lo sumo uno de los dos, ninguno es un
    # consentimiento general no ligado a algo especifico.
    procedure_planned_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("procedures_planned.id", ondelete="SET NULL"),
        nullable=True,
    )
    treatment_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("treatment_plans.id", ondelete="SET NULL"), nullable=True
    )
    professional_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    signer_name: Mapped[str] = mapped_column(String(200))
    signer_relationship: Mapped[str] = mapped_column(String(10))
    signature_path: Mapped[str] = mapped_column(String(500))
    pdf_path: Mapped[str] = mapped_column(String(500))
    content_hash: Mapped[str] = mapped_column(String(64))
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
