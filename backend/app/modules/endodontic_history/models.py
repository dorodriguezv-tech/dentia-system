"""Fase F (rediseno del expediente, docs/clinica): Historia Clinica de
Endodoncia -- interrogatorio (antecedentes/dolor/estimulo) + examen
intrabucal/extrabucal, pruebas de sensibilidad pulpar, pruebas periodontales,
interpretacion radiografica, diagnostico y tratamiento, odontograma de 18
codigos (diagnostico Y evolucion, misma tabla con discriminador `kind`) y
longitud de trabajo con datos de tratamiento por pieza.

Paquete nuevo (no extension de `records/`, `odontological_history/` ni
`pediatric_history/`): mismo patron de paquete completo que ambos (CLAUDE.md
sec. 3). Mismo patron `_AnnullableMixin` (regla 2: sin borrado fisico, se
anula con motivo) + `AuditedMixin` (regla 6: fecha, autor);
`clinic_id`/`patient_id`/`encounter_id` en todas las tablas. Todas las tablas
son "una fila por encounter" excepto `EndodonticPulpSensitivityTest` (varias
pruebas por encounter, el PDF muestra 2 bloques identicos pero no hay limite
clinico de 2) y `EndodonticToothDiagnosisCode` (varias filas por encounter,
una por pieza+kind anotada -- ver decision de re-anotacion documentada ahi
mismo, mismo patron que `PediatricToothAnnotation` de la Fase E).

NO se toca el catalogo general del odontograma (`app.modules.odontogram`,
Fase B): los 18 codigos de endodoncia son un catalogo propio, exclusivo de
esta historia.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import AuditedMixin, Base


class _AnnullableMixin:
    """Regla 2 de CLAUDE.md: sin borrado fisico, se anula con motivo y queda
    auditado. Duplicada a proposito (igual que records/odontological_history/
    pediatric_history/etc.): es privada al modulo, no se importa entre
    paquetes en este repo."""

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    annul_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    annulled_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    annulled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EndodonticInterrogation(_AnnullableMixin, AuditedMixin, Base):
    """1. Interrogatorio (antecedentes/dolor/estimulo) + examen intrabucal +
    examen extrabucal. Los 5 checklists son `dict[str, bool]` con claves
    fijas (ver `rules.py`), NO catalogo administrable."""

    __tablename__ = "endodontic_interrogations"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    antecedentes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    antecedentes_otro_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    dolor: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    dolor_otro_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimulo: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    estimulo_otro_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    examen_intrabucal: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    examen_intrabucal_otro_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    examen_extrabucal: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    examen_extrabucal_otro_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class EndodonticPulpSensitivityTest(_AnnullableMixin, AuditedMixin, Base):
    """2. Pruebas de sensibilidad pulpar -- varias filas por encounter (el PDF
    muestra 2 bloques identicos lado a lado, pero no hay limite clinico de
    exactamente 2 pruebas)."""

    __tablename__ = "endodontic_pulp_sensitivity_tests"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    frio: Mapped[bool] = mapped_column(Boolean, default=False)
    calor: Mapped[bool] = mapped_column(Boolean, default=False)
    fugaz: Mapped[bool] = mapped_column(Boolean, default=False)
    persistente: Mapped[bool] = mapped_column(Boolean, default=False)
    localizado: Mapped[bool] = mapped_column(Boolean, default=False)
    irradiado: Mapped[bool] = mapped_column(Boolean, default=False)
    decrece: Mapped[bool] = mapped_column(Boolean, default=False)
    incrementa: Mapped[bool] = mapped_column(Boolean, default=False)
    diente_testigo_od: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prueba_cavidad: Mapped[str | None] = mapped_column(String(200), nullable=True)
    prueba_electrica_od: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class EndodonticPeriodontalTest(_AnnullableMixin, AuditedMixin, Base):
    """3. Pruebas periodontales -- una fila por encounter. Percusion
    horizontal y vertical son 2 columnas del MISMO formulario (no entradas
    repetibles)."""

    __tablename__ = "endodontic_periodontal_tests"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    percusion_horizontal: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    movilidad_horizontal: Mapped[str | None] = mapped_column(String(10), nullable=True)
    movilidad_horizontal_grado: Mapped[str | None] = mapped_column(String(3), nullable=True)
    percusion_vertical: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    movilidad_vertical: Mapped[str | None] = mapped_column(String(10), nullable=True)
    movilidad_vertical_grado: Mapped[str | None] = mapped_column(String(3), nullable=True)
    palpacion: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class EndodonticRadiographicInterpretation(_AnnullableMixin, AuditedMixin, Base):
    """4. Interpretacion radiografica (camara/conducto/periodonto) -- una fila
    por encounter."""

    __tablename__ = "endodontic_radiographic_interpretations"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    camara: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    camara_otro_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    conducto: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    conducto_otro_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)
    periodonto: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    periodonto_otro_detalle: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class EndodonticDiagnosisTreatment(_AnnullableMixin, AuditedMixin, Base):
    """5. Diagnostico pulpar/periapical (seleccion unica cada uno) y
    tratamiento/cirugia (multi-select) -- una fila por encounter."""

    __tablename__ = "endodontic_diagnosis_treatments"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    diagnostico_pulpar: Mapped[str | None] = mapped_column(String(30), nullable=True)
    diagnostico_periapical: Mapped[str | None] = mapped_column(String(30), nullable=True)
    tratamiento: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    cirugia: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class EndodonticToothDiagnosisCode(_AnnullableMixin, AuditedMixin, Base):
    """6. Odontograma de diagnostico Y de evolucion -- 18 codigos numericos
    (0-17) propios de endodoncia (catalogo independiente del catalogo general
    del odontograma, Fase B -- NO se toca `app.modules.odontogram`). El PDF
    repite el mismo dibujo dos veces (diagnostico inicial / evolucion del
    tratamiento): se modela como UNA tabla con el discriminador `kind`
    ("diagnostico"|"evolucion") en vez de duplicar la tabla.

    Solo piezas FDI permanentes (`rules.TOOTH_FDI_PERMANENT_CODES`, reutiliza
    `app.modules.odontogram.rules.TOOTH_FDI_PERMANENT`).

    Decision de re-anotacion (igual patron que
    `pediatric_history.PediatricToothAnnotation`, Fase E):
    si se vuelve a anotar la MISMA pieza con el MISMO `kind` en el MISMO
    encounter, la anotacion activa anterior de esa pieza+kind se anula
    automaticamente (motivo autogenerado) antes de crear la nueva -- solo una
    vigente por pieza+kind. Una pieza puede tener una anotacion `diagnostico`
    Y una `evolucion` simultaneamente activas (son independientes), pero no
    dos `diagnostico` activas a la vez para la misma pieza."""

    __tablename__ = "endodontic_tooth_diagnosis_codes"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    tooth_fdi: Mapped[str] = mapped_column(String(2))
    kind: Mapped[str] = mapped_column(String(15))
    code: Mapped[int] = mapped_column(SmallInteger)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class EndodonticWorkingLength(_AnnullableMixin, AuditedMixin, Base):
    """7. Longitud de trabajo + datos de tratamiento -- una fila por
    encounter (documenta el tratamiento de UNA pieza por visita, con sus
    conductos). `canal_measurements` es un JSONB
    {clave_conducto: {aparente_rx, real_localizador, relacion}} donde
    `clave_conducto` es una de `rules.CANAL_KEYS`."""

    __tablename__ = "endodontic_working_lengths"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    tooth_fdi: Mapped[str | None] = mapped_column(String(2), nullable=True)
    canal_measurements: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    tecnica_instrumentacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    tecnica_obturacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    indicaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Texto libre a proposito (no Date): igual criterio que
    # `fecha_ultima_visita_dentista` de Fase E -- el formato original no exige
    # fecha ISO verificada, es un campo de captura libre del expediente fisico.
    fecha_inicio: Mapped[str | None] = mapped_column(String(100), nullable=True)
    fecha_termino: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")
