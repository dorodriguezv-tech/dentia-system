"""Fase G (rediseno del expediente, docs/clinica): Periodontograma completo --
ULTIMO slice del proyecto. Sondeo periodontal de 6 sitios por pieza
(profundidad de sondaje + recesion + sangrado al sondaje + supuracion),
medicion por pieza (movilidad de Miller + grado de furca), indices de placa
dentobacteriana/gingival por cara, tablas de oclusion (contactos marcados por
movimiento) y observaciones.

Cierra formalmente el pendiente dejado abierto desde la Fase C (ver
docs/PENDIENTES_CLINICOS.md #59): `odontological_history.PeriodontalAnamnesis`
(Fase C) es solo un CUESTIONARIO DE ENTREVISTA, nunca sondeo clinico -- este
paquete es el sondeo clinico que faltaba, y NO se agrega a
`odontological_history/` (paquete nuevo, mismo criterio de "un paquete por
modulo, vertical slice" que el resto de las fases del rediseno).

Fuente de verdad: la pagina "PERIODONTOGRAMA" y las de "INDICE DE PLACA
DENTOBACTERIANA"/"INDICE GINGIVAL" del PDF oficial "historia clinca
odontologica.pdf" son una cuadricula dibujada a mano (no texto estructurado):
las etiquetas de fila exactas (E.Q/E.I/N.I/P.B., repetidas de forma algo
ambigua en el escaneo) no se pudieron transcribir pixel-perfecto. Ante esa
ambiguedad, el modelo de datos sigue el ESTANDAR CLINICO PERIODONTAL
UNIVERSAL (6 sitios de sondeo por pieza, movilidad de Miller 0-3, grado de
furca 0-3, indice de placa de O'Leary y gingival de Loe-Silness) -- mismo
criterio que el resto del proyecto ante ambiguedad del formato original
(catalogo/diseno razonable, documentado en docs/PENDIENTES_CLINICOS.md para
validar con la clinica real).

Paquete nuevo `app/modules/periodontogram/` (mismo patron de paquete completo
que `odontological_history/`/`pediatric_history/`/`endodontic_history/`:
`models.py`/`schemas.py`/`rules.py`/`service.py`/`router.py`/`pdf.py`). Mismo
patron `_AnnullableMixin` (regla 2 de CLAUDE.md: sin borrado fisico, se anula
con motivo) + `AuditedMixin` (regla 6: fecha, autor); `clinic_id`/
`patient_id`/`encounter_id` en todas las tablas.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import AuditedMixin, Base


class _AnnullableMixin:
    """Regla 2 de CLAUDE.md: sin borrado fisico, se anula con motivo y queda
    auditado. Duplicada a proposito (igual que odontological_history/
    pediatric_history/endodontic_history/etc.): es privada al modulo, no se
    importa entre paquetes en este repo."""

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    annul_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    annulled_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    annulled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PeriodontalProbingSite(_AnnullableMixin, AuditedMixin, Base):
    """1. Sondeo periodontal -- el periodontograma propiamente dicho: 6
    sitios por pieza (mesiovestibular/vestibular/distovestibular/
    mesiolingual/lingual/distolingual -- "lingual" aplica igual para la
    arcada superior, donde clinicamente es "palatino": es solo una etiqueta
    de interfaz, ver `rules.PROBING_SITE_LABELS`, el codigo no cambia). Varias
    filas por encounter (una por pieza x sitio). Solo piezas FDI PERMANENTES
    (`rules.is_valid_permanent_tooth_code`, el dibujo del PDF no muestra
    temporales).

    Nivel de inserccion clinica (CAL, "clinical attachment level") NO se
    persiste: se calcula al vuelo como `probing_depth_mm + recession_mm`
    (mismo criterio que el IMC de la Fase A, `records/rules.py::
    body_mass_index` -- dato derivado nunca desincronizado), expuesto en el
    schema Out como `clinical_attachment_level_mm`.

    Decision de re-anotacion (igual patron que
    `pediatric_history.PediatricToothAnnotation`/
    `endodontic_history.EndodonticToothDiagnosisCode`, ver
    docs/PENDIENTES_CLINICOS.md): volver a capturar la MISMA pieza+sitio en
    el MISMO encounter anula automaticamente la anotacion activa anterior de
    esa pieza+sitio (motivo autogenerado) antes de crear la nueva -- solo una
    vigente por pieza+sitio."""

    __tablename__ = "periodontal_probing_sites"

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
    site: Mapped[str] = mapped_column(String(20))
    probing_depth_mm: Mapped[int] = mapped_column(SmallInteger)
    # Puede ser negativo: agrandamiento/cobertura gingival sobre la union
    # cemento-esmalte (caso raro pero valido clinicamente).
    recession_mm: Mapped[int] = mapped_column(SmallInteger)
    bleeding_on_probing: Mapped[bool] = mapped_column(Boolean, default=False)
    suppuration: Mapped[bool] = mapped_column(Boolean, default=False)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class PeriodontalToothMeasurement(_AnnullableMixin, AuditedMixin, Base):
    """2. Medicion por pieza (NO por sitio): movilidad dentaria (clasificacion
    de Miller, 0 sin movilidad - 3 grados crecientes) y grado de afectacion de
    furca (0-3, relevante en molares pero el codigo no restringe la pieza).
    Varias filas por encounter (una por pieza). Solo piezas FDI permanentes.

    Decision de re-anotacion: igual patron que `PeriodontalProbingSite` --
    volver a medir la MISMA pieza en el MISMO encounter anula automaticamente
    la medicion activa anterior de esa pieza."""

    __tablename__ = "periodontal_tooth_measurements"

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
    mobility_grade: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    furcation_grade: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class PeriodontalIndexEntry(_AnnullableMixin, AuditedMixin, Base):
    """3. Indices de placa dentobacteriana y gingival -- UNA sola tabla con
    discriminador `index_type` (igual patron que `kind` en
    `endodontic_history.EndodonticToothDiagnosisCode`, en vez de duplicar la
    tabla). Varias filas por encounter (una por pieza x superficie x
    index_type). Solo 2 superficies por pieza (vestibular/lingual -- "lingual"
    equivale a lingual/palatino segun la arcada, igual criterio de etiqueta de
    interfaz que el sitio de sondeo), NO 6 sitios: el PDF muestra una
    cuadricula mucho mas simple para los indices que para el periodontograma
    de sondeo. `grade` 0-3, cuyo significado depende de `index_type` (ver
    `rules.PLAQUE_GRADE_LABELS`/`GINGIVAL_GRADE_LABELS`):
    - placa: 0 ausencia de placa, 1 en 1/3 de la superficie, 2 en 2/3, 3 en
      mas de 2/3.
    - gingival: 0 normal (encia sana), 1 leve (cambio de color/edema leve,
      sin sangrado al sondaje), 2 moderada (enrojecimiento evidente, sangrado
      al sondaje), 3 severa (enrojecimiento/edema severo, ulceracion,
      tendencia a sangrado espontaneo).

    Los totales (indice de placa dentobacteriana de O'Leary, indice gingival
    de Loe-Silness) NO se persisten: se calculan al vuelo en
    `GET .../indices-summary` (ver `rules.compute_plaque_index`/
    `compute_gingival_index` y `service.py`).

    Decision de re-anotacion: volver a capturar la MISMA
    pieza+index_type+surface en el MISMO encounter anula automaticamente la
    anotacion activa anterior de esa combinacion."""

    __tablename__ = "periodontal_index_entries"

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
    index_type: Mapped[str] = mapped_column(String(10))
    surface: Mapped[str] = mapped_column(String(15))
    grade: Mapped[int] = mapped_column(SmallInteger)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class OcclusalContactEntry(_AnnullableMixin, AuditedMixin, Base):
    """4. Tablas de oclusion -- contactos oclusales marcados en 4 movimientos
    (centrica/lateralidad izquierda/protrusion/lateralidad derecha). Varias
    filas por encounter (una por pieza x movimiento), pero SOLO se crea una
    fila cuando el contacto esta marcado: si no hay fila para una
    pieza+movimiento, significa "sin contacto marcado" -- no se crean filas
    explicitas en falso. No tiene `grade` ni campo adicional: la EXISTENCIA
    de la fila activa ES la marca de "en contacto". Permite varias piezas
    marcadas por movimiento (lista de piezas en contacto por cada uno de los
    4 movimientos).

    Decision (`service.py::create_occlusal_contact`): volver a marcar la
    MISMA pieza+movimiento en el MISMO encounter es idempotente -- devuelve
    la fila activa existente en vez de crear un duplicado (no hay "grado" que
    actualizar, solo un estado de presencia); para "desmarcar" se usa el
    endpoint de anulacion."""

    __tablename__ = "occlusal_contact_entries"

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
    movement: Mapped[str] = mapped_column(String(25))

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class PeriodontogramObservation(_AnnullableMixin, AuditedMixin, Base):
    """5. Observaciones del periodontograma -- una fila por encounter (mismo
    criterio que el resto del expediente: no se impone fila unica por
    encuentro, se corrige anulando y recapturando)."""

    __tablename__ = "periodontogram_observations"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")
