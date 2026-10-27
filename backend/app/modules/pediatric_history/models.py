"""Fase E (rediseno del expediente, docs/clinica): Historia Clinica Pediatrica
-- antecedentes perinatales y primer ano de vida, habitos y antecedentes
bucales, madurez y conducta, oclusion y alineamiento, erupcion y denticion, y
anotaciones del odontograma pediatrico (anomalias por pieza, incluida la
distincion ausente congenito/adquirida -- ver nota en rules.py). El plan de
tratamiento permanente/temporal NO vive aqui: reutiliza
`odontological_history.ToothTreatmentPlanEntry` (Fase C), ampliada en esta
fase para aceptar tambien piezas temporales.

Paquete nuevo (no extension de `records/` ni de `odontological_history/`):
mismo patron de paquete completo que ambos (CLAUDE.md sec. 3). Mismo patron
`_AnnullableMixin` (regla 2: sin borrado fisico, se anula con motivo) +
`AuditedMixin` (regla 6: fecha, autor); `clinic_id`/`patient_id`/`encounter_id`
en todas las tablas. Todas las tablas son "una fila por encounter" excepto
`PediatricToothAnnotation`, que naturalmente tiene varias filas por encounter
(una por pieza anotada) -- ver decision de re-anotacion documentada ahi mismo
y en docs/PENDIENTES_CLINICOS.md.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import AuditedMixin, Base


class _AnnullableMixin:
    """Regla 2 de CLAUDE.md: sin borrado fisico, se anula con motivo y queda
    auditado. Duplicada a proposito (igual que diagnosis/documents/imaging/
    treatment/odontological_history): es privada al modulo, no se importa
    entre paquetes en este repo."""

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    annul_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    annulled_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    annulled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PediatricPerinatalHistory(_AnnullableMixin, AuditedMixin, Base):
    """1. Antecedentes perinatales y primer ano de vida."""

    __tablename__ = "pediatric_perinatal_histories"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    problemas_embarazo_perinatales: Mapped[str | None] = mapped_column(Text, nullable=True)
    tomo_medicamentos_embarazo: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    tomo_medicamentos_embarazo_cuales: Mapped[str | None] = mapped_column(Text, nullable=True)
    embarazo_observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    tomo_medicamentos_primer_ano: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    tomo_medicamentos_primer_ano_cuales: Mapped[str | None] = mapped_column(Text, nullable=True)
    vacunas_completas: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fecha_ultima_visita_dentista: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class PediatricOralHabits(_AnnullableMixin, AuditedMixin, Base):
    """2. Habitos y antecedentes bucales -- todas Si/No simple."""

    __tablename__ = "pediatric_oral_habits"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    cepilla_despues_alimento: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    sangran_encias_sin_cepillar: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    sabe_que_es_fluor: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fluoruro_sistematico_aplicado: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    diente_extraido: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    accidentes_fracturas_dentales: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    dolor_dental_reciente: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    bruxismo_nocturno: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    respira_boca_frecuente: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class PediatricBehaviorMaturity(_AnnullableMixin, AuditedMixin, Base):
    """3. Madurez y conducta. `caracter` es un catalogo administrable
    (`pediatric_character`)."""

    __tablename__ = "pediatric_behavior_maturities"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    experiencia_desfavorable_dentista: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    se_relaciona_medico: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    controla_esfinteres: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    toma_biberon_actualmente: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # Texto libre a proposito (no booleano): el PDF original pregunta "¿A que
    # edad dejo el biberon?" en texto a pesar de un error de imprenta que
    # muestra casillas Si/No ahi -- ver nota del encargo / PENDIENTES_CLINICOS.
    edad_dejo_biberon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    succion_labio_dedo: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    muerde_objetos_unas: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    relacion_otros_ninos: Mapped[str | None] = mapped_column(Text, nullable=True)
    caracter: Mapped[str | None] = mapped_column(String(40), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class PediatricOcclusion(_AnnullableMixin, AuditedMixin, Base):
    """4. Oclusion y alineamiento. `planos_terminales_*` y son catalogo
    administrable (`terminal_plane`); `linea_media`/`clasificacion_angle` son
    Literal fijos (opciones cerradas explicitas del PDF)."""

    __tablename__ = "pediatric_occlusions"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    planos_terminales_izq: Mapped[str | None] = mapped_column(String(40), nullable=True)
    planos_terminales_der: Mapped[str | None] = mapped_column(String(40), nullable=True)
    angle_molar_izq: Mapped[str | None] = mapped_column(String(200), nullable=True)
    angle_molar_der: Mapped[str | None] = mapped_column(String(200), nullable=True)
    overjet_mm: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    overbite_mm: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    mordida_cruzada: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    diastema: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    mordida_abierta_ante_mm: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    mordida_abierta_post_mm: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    linea_media: Mapped[str | None] = mapped_column(String(25), nullable=True)
    clasificacion_angle: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class PediatricEruptionDentition(_AnnullableMixin, AuditedMixin, Base):
    """5. Erupcion y denticion. La tabla estatica de cronologia de erupcion/
    caida del PDF (incisivo central 8-12 meses erupcion / 6-7 anos se cae,
    etc.) NO se captura aqui -- es contenido de referencia fijo, ver
    `rules.PRIMARY_TOOTH_ERUPTION_CHRONOLOGY`/`PERMANENT_TOOTH_ERUPTION_CHRONOLOGY`."""

    __tablename__ = "pediatric_eruption_dentitions"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    secuencia_normal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    perdida_prematura: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    retencion_prolongada: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    erupcion_retardada: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    falta_contacto_proximal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    malposicion_dentaria: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    otras_anormalidades: Mapped[str | None] = mapped_column(Text, nullable=True)
    edad_dental: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estado_general_higiene: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class PediatricToothAnnotation(_AnnullableMixin, AuditedMixin, Base):
    """6. Odontograma pediatrico -- anotaciones de anomalia por pieza. A
    diferencia de las 5 tablas anteriores (una fila por encounter), esta tiene
    varias filas por encounter: una por pieza anotada. `tooth_fdi` se valida
    contra `app.modules.odontogram.rules.TOOTH_FDI_ALL` (permanentes Y
    temporales, via `rules.is_valid_tooth_code`); `anomaly_code` es el catalogo
    administrable `pediatric_tooth_anomaly` (incluye `ausente_congenito` /
    `ausente_adquirida`, ver nota de correccion en rules.py -- NO toca el
    catalogo global `odontogram_finding` de la Fase B).

    Decision de re-anotacion (docs/PENDIENTES_CLINICOS.md): si se vuelve a
    anotar la MISMA pieza en el MISMO encounter, la anotacion activa anterior
    para esa pieza se anula automaticamente (motivo autogenerado) antes de
    crear la nueva -- mismo criterio de "una vigente" que la regla 5 de
    CLAUDE.md aplica al odontograma general, aplicado aqui a esta anotacion
    exclusiva de la Historia Pediatrica. No se permiten varias anotaciones
    activas simultaneas para la misma pieza+encounter."""

    __tablename__ = "pediatric_tooth_annotations"

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
    anomaly_code: Mapped[str] = mapped_column(String(40))
    # Texto libre a proposito (notacion ambigua en el propio PDF original,
    # "1/3 2/3 3/3" o "i/c/ce") -- ver docs/PENDIENTES_CLINICOS.md.
    hipoplasia_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")
