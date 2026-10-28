"""Fase D (docs/clinica, "Documentos imprimibles nuevos"): Receta, Hoja de
referencia/interconsulta y Hoja de contrarreferencia.

A diferencia de `Consent` (documents/models.py), estos documentos NO llevan
firma digital capturada en pantalla -- el formato oficial los imprime con un
espacio en blanco para firmarse a mano (regla de negocio confirmada con el
usuario: "NO implementes firma digital aqui"). Por eso no hay `pdf_path` ni
`content_hash`: el PDF se genera al vuelo cada vez que se pide (mismo patron
que el presupuesto de tratamiento, `treatment/pdf.py`), leyendo en ese momento
los datos vigentes del paciente (alergias, signos vitales) en vez de
duplicarlos aqui -- menos redundancia, igual criterio que
`records/service.py::generate_general_history_pdf`.

Una vez creado, un documento no se edita (regla 2 de CLAUDE.md: sin borrado
fisico): un dato incorrecto se corrige anulando este registro con motivo y
capturando uno nuevo, igual que `Consent`."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
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


class Prescription(_AnnullableMixin, AuditedMixin, Base):
    """Receta medica (docs/clinica/receta.pdf). El PDF imprime DOS copias
    identicas de esta misma receta apiladas en una sola hoja carta (decision
    confirmada con el usuario: "mantén la dimensión... 2 recetas en una sola
    hoja") -- eso es asunto del renderizador (clinical_documents/pdf.py), no
    de este modelo: aqui se guarda una sola receta.

    `folio`: consecutivo simple por clinica (ver
    clinical_documents/service.py::_next_prescription_folio) -- decision
    documentada ahi, no es el UUID de la fila para que sea legible/corto en
    el papel impreso.
    `medications`: JSONB `[{"nombre": str, "detalle": str}]` -- "detalle" es
    una sola celda de texto libre con forma farmaceutica/dosis/presentacion/
    frecuencia/via/duracion/indicaciones, tal como lo muestra el formato
    oficial (el usuario autorizo esta simplificacion en vez de columnas
    separadas)."""

    __tablename__ = "prescriptions"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )
    folio: Mapped[str] = mapped_column(String(40))
    diagnostico: Mapped[str] = mapped_column(Text)
    medications: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)


class ReferralNote(_AnnullableMixin, AuditedMixin, Base):
    """Hoja de referencia/interconsulta
    (docs/clinica/hoja de referencia_interconsulta.pdf). Los campos que el
    formato autollena (diagnosticos/medicamentos/alergias/tratamientos) se
    guardan como el texto final que capturo el dentista (el frontend los
    prellena desde el expediente, pero lo que se persiste es ese texto, no
    una referencia viva) -- por eso son nullable: el autollenado puede
    dejarlos vacios para edicion manual. `motivo_interconsulta` es el dato
    central del documento y si es obligatorio."""

    __tablename__ = "referral_notes"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )
    diagnosticos: Mapped[str | None] = mapped_column(Text, nullable=True)
    medicamentos_texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    alergias_texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    tratamientos_texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    motivo_interconsulta: Mapped[str] = mapped_column(Text)
    establecimiento_receptor: Mapped[str] = mapped_column(String(300))


class CounterReferralNote(_AnnullableMixin, AuditedMixin, Base):
    """Hoja de contrarreferencia (docs/clinica/hoja de contrareferencia.pdf).
    `referral_note_id` es un enlace OPCIONAL a la referencia original que se
    esta respondiendo (el formato en papel solo pide describirla en texto
    libre via `motivo_interconsulta_original`, no exige el vinculo)."""

    __tablename__ = "counter_referral_notes"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )
    referral_note_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("referral_notes.id", ondelete="SET NULL"), nullable=True
    )
    motivo_contrarreferencia: Mapped[str] = mapped_column(Text)
    tratamientos_texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    motivo_interconsulta_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    establecimiento_emisor: Mapped[str] = mapped_column(String(300))
