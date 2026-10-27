"""Fase C (rediseno del expediente, docs/clinica): Historia Clinica
Odontologica -- exploracion cabeza/cuello + ATM + tejidos blandos, anamnesis
periodontal (cuestionario de entrevista, NO sondeo clinico -- eso es la
Fase G/periodontograma completo), auxiliares de diagnostico (radiografico),
datos complementarios del odontograma de diagnostico (Kennedy, espacio
protesico, analisis para protesis fija), analisis con paralelometro, diseno
de protesis parcial removible y diagnostico/plan de tratamiento por organo
dental.

Paquete nuevo (no una extension de `records/`): `records/service.py` ya tenia
1020 lineas y `records/router.py` 455 antes de esta fase; agregar 8 tablas mas
con su CRUD+anulacion hubiera dejado esos archivos en >1900/~900 lineas,
dificiles de mantener. Se sigue el mismo patron de paquete completo que
`document_settings/` (CLAUDE.md sec. 3: "un paquete por modulo, vertical
slice"), reutilizando los catalogos y utilidades de Fase A
(`app.modules.catalogs`, `app.modules.odontogram.rules` para validar FDI) en
vez de duplicarlos.

Mismo patron que el resto del expediente: `_AnnullableMixin` (regla 2: sin
borrado fisico, se anula con motivo) + `AuditedMixin` (regla 6: fecha, autor);
`clinic_id`/`patient_id`/`encounter_id` en todas las tablas (regla 6: contexto
de encounter); ninguna impone fila unica por encuentro -- se corrige anulando
y recapturando, igual que Fase A.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import AuditedMixin, Base


class _AnnullableMixin:
    """Regla 2 de CLAUDE.md: sin borrado fisico, se anula con motivo y queda auditado.
    Duplicada a proposito (igual que diagnosis/documents/imaging/treatment): es
    privada al modulo, no se importa entre paquetes en este repo."""

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    annul_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    annulled_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    annulled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OdontologicalExam(_AnnullableMixin, AuditedMixin, Base):
    """Exploracion de cabeza y cuello + biotipo facial + ATM + tejidos blandos
    (pagina 1 de "historia clinca odontologica.pdf"). `skull_type` y
    `facial_biotype` son catalogos administrables (app.modules.catalogs)."""

    __tablename__ = "odontological_exams"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    skull_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    facial_biotype: Mapped[str | None] = mapped_column(String(40), nullable=True)
    facial_biotype_observations: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ATM
    apertura_conservada_mm: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    apertura_limitada_mm: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    chasquidos_derecho: Mapped[bool] = mapped_column(Boolean, default=False)
    crepitacion_derecho: Mapped[bool] = mapped_column(Boolean, default=False)
    chasquidos_izquierdo: Mapped[bool] = mapped_column(Boolean, default=False)
    crepitacion_izquierdo: Mapped[bool] = mapped_column(Boolean, default=False)
    dolor_apertura_lateralidad: Mapped[bool] = mapped_column(Boolean, default=False)
    fatiga_dolor_muscular: Mapped[bool] = mapped_column(Boolean, default=False)
    desviacion_apertura_cierre: Mapped[bool] = mapped_column(Boolean, default=False)
    atm_observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tejidos blandos
    ganglios: Mapped[str | None] = mapped_column(Text, nullable=True)
    carrillos: Mapped[str | None] = mapped_column(Text, nullable=True)
    labios: Mapped[str | None] = mapped_column(Text, nullable=True)
    lengua: Mapped[str | None] = mapped_column(Text, nullable=True)
    piso_boca: Mapped[str | None] = mapped_column(Text, nullable=True)
    region_retromolar: Mapped[str | None] = mapped_column(Text, nullable=True)
    paladar_duro_blando: Mapped[str | None] = mapped_column(Text, nullable=True)
    faringe: Mapped[str | None] = mapped_column(Text, nullable=True)
    encia_libre_marginal: Mapped[str | None] = mapped_column(Text, nullable=True)
    tejidos_blandos_observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class PeriodontalAnamnesis(_AnnullableMixin, AuditedMixin, Base):
    """Anamnesis periodontal: cuestionario de entrevista (NO sondeo clinico --
    el periodontograma completo con sondeo de 6 sitios/diente e indices de
    placa/gingival queda para la Fase G, ver docs/PENDIENTES_CLINICOS.md).
    `answers` es un JSONB {codigo_pregunta: "si"|"no"|"no_recuerda"} validado
    contra el catalogo administrable "periodontal_anamnesis_question"."""

    __tablename__ = "periodontal_anamneses"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    answers: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Campos complementarios de texto libre (no son catalogo, columnas propias).
    cepillado_veces_dia: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    cepillado_pasta: Mapped[str | None] = mapped_column(String(200), nullable=True)
    insatisfaccion_motivo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    tratamiento_medico_detalle: Mapped[str | None] = mapped_column(String(300), nullable=True)
    medicamento_actual: Mapped[str | None] = mapped_column(String(300), nullable=True)
    cirugia_detalle: Mapped[str | None] = mapped_column(String(300), nullable=True)
    hormonas_para_que: Mapped[str | None] = mapped_column(String(300), nullable=True)
    habito_danino_cual: Mapped[str | None] = mapped_column(String(300), nullable=True)
    fuma_cigarros_dia: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    alcohol_veces_semana: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    # Texto libre (no date): el paciente rara vez recuerda la fecha exacta de su
    # ultimo examen odontologico ("hace 2 anos", "no recuerdo") -- es un
    # cuestionario de entrevista, no un dato clinico verificado.
    ultimo_examen_odontologico: Mapped[str | None] = mapped_column(String(100), nullable=True)
    salud_bucal_autopercibida: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class RadiographicAnalysis(_AnnullableMixin, AuditedMixin, Base):
    """Auxiliares de diagnostico -- analisis radiografico. `findings` es un
    JSONB {tipo: {organos_dentarios, porcentaje, alteracion}} donde `tipo` es
    uno de los 5 fijos de `rules.RADIOGRAPHIC_FINDING_TYPES` (no necesitan
    catalogo administrable, lo dice la especificacion). `anexos_nota` es solo
    una referencia textual a fotografias/radiografias/panoramica -- adjuntar
    el archivo en si ya lo resuelve `app.modules.imaging`, no se duplica."""

    __tablename__ = "radiographic_analyses"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    findings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    anexos_nota: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class OdontogramDiagnosisDetail(_AnnullableMixin, AuditedMixin, Base):
    """Odontograma de diagnostico -- datos complementarios que no son el dibujo
    en si (eso ya existe desde la Fase B, `app.modules.odontogram`): espacio
    protesico, clasificacion de Kennedy superior/inferior y el analisis de
    organos dentales indicados para protesis fija."""

    __tablename__ = "odontogram_diagnosis_details"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    edentulous_space_available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    edentulous_space_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    kennedy_sup_class: Mapped[str | None] = mapped_column(String(3), nullable=True)
    kennedy_sup_modification: Mapped[bool] = mapped_column(Boolean, default=False)
    kennedy_inf_class: Mapped[str | None] = mapped_column(String(3), nullable=True)
    kennedy_inf_modification: Mapped[bool] = mapped_column(Boolean, default=False)
    fixed_prosthesis_analysis: Mapped[list[Any]] = mapped_column(JSONB, default=list)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class ParallelometerAnalysis(_AnnullableMixin, AuditedMixin, Base):
    """Analisis con paralelometro: lista de organos dentales con caracteristicas
    y plan de tratamiento (previo a disenar la protesis parcial removible)."""

    __tablename__ = "parallelometer_analyses"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    entries: Mapped[list[Any]] = mapped_column(JSONB, default=list)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class RemovablePartialDentureDesign(_AnnullableMixin, AuditedMixin, Base):
    """Diseno de protesis parcial removible: los 6 componentes del formato, cada
    uno texto libre (descripcion del componente elegido, no un catalogo)."""

    __tablename__ = "removable_partial_denture_designs"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    conector_mayor: Mapped[str | None] = mapped_column(Text, nullable=True)
    conector_menor: Mapped[str | None] = mapped_column(Text, nullable=True)
    retenedores_directos: Mapped[str | None] = mapped_column(Text, nullable=True)
    conectores_indirectos: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_protesica: Mapped[str | None] = mapped_column(Text, nullable=True)
    dientes_artificiales: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class ToothDiagnosisEntry(_AnnullableMixin, AuditedMixin, Base):
    """Diagnostico por organo dental: `diagnoses` es un JSONB {tooth_fdi: texto}
    -- las claves se validan contra piezas FDI permanentes (11-18/21-28/31-38/
    41-48, ver rules.py) reutilizando el catalogo de piezas de
    app.modules.odontogram, no se duplica."""

    __tablename__ = "tooth_diagnosis_entries"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    diagnoses: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class ToothTreatmentPlanEntry(_AnnullableMixin, AuditedMixin, Base):
    """Plan de tratamiento por organo dental: misma estructura que
    `ToothDiagnosisEntry` pero para el plan (`plans`), regla 3 de CLAUDE.md
    (lo planificado no equivale a lo realizado) -- esto es solo el plan
    propuesto por pieza, `ProcedurePlanned`/`ProcedurePerformed` (modulo
    `treatment`) siguen siendo las entidades operativas del plan real."""

    __tablename__ = "tooth_treatment_plan_entries"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    plans: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")
