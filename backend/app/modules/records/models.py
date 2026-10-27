import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text
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


class MedicalHistory(_AnnullableMixin, AuditedMixin, Base):
    __tablename__ = "medical_history"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )
    category: Mapped[str] = mapped_column(String(30))
    text: Mapped[str] = mapped_column(Text)
    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class Allergy(_AnnullableMixin, AuditedMixin, Base):
    __tablename__ = "allergies"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )
    substance: Mapped[str] = mapped_column(String(200))
    reaction: Mapped[str | None] = mapped_column(String(300), nullable=True)
    severity: Mapped[str] = mapped_column(String(10))
    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class Medication(_AnnullableMixin, AuditedMixin, Base):
    __tablename__ = "medications"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(String(200))
    dose: Mapped[str | None] = mapped_column(String(100), nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class VitalSigns(AuditedMixin, Base):
    __tablename__ = "vital_signs"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    bp_systolic: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    bp_diastolic: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    heart_rate: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    temperature: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    # Fase A (rediseno del expediente, docs/clinica): campos que pide el
    # formato de signos vitales de la Historia Clinica General. El IMC se
    # calcula al vuelo a partir de height_m/weight_kg (no se persiste, evita
    # datos derivados desincronizados -- ver records/rules.py::body_mass_index).
    height_m: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    spo2: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    glucose_index: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    glucose_timing: Mapped[str | None] = mapped_column(String(15), nullable=True)
    patient_attitude: Mapped[str | None] = mapped_column(String(20), nullable=True)
    asa_classification: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


# --------------------------------------------------------------------------------
# Fase A (rediseno del expediente segun formatos oficiales, docs/clinica): Historia
# Clinica General -- heredofamiliares, antecedentes personales patologicos/no
# patologicos e interrogatorio por aparatos y sistemas. Se agregan junto a
# MedicalHistory/Allergy/Medication/VitalSigns (que se conservan intactos, siguen
# alimentando las alertas de rules.py con texto libre); estas tablas nuevas cubren
# los campos tabulados que pide el formato oficial sin reemplazar nada existente.
# Mismo patron (_AnnullableMixin + AuditedMixin, clinic_id/patient_id/encounter_id
# por regla 6 de CLAUDE.md: fecha/autor/contexto) que el resto del modulo.
# --------------------------------------------------------------------------------


class FamilyHistoryEntry(_AnnullableMixin, AuditedMixin, Base):
    """Un renglon de la tabla de heredofamiliares (un pariente por fila). El
    parentesco es un catalogo administrable (catalog_type="family_relationship");
    `conditions` es un JSONB {codigo_de_condicion: marcado} en vez de ~16 columnas
    booleanas -- mas simple y extensible via catalogo
    (catalog_type="family_condition"), igual criterio que odontogram_finding."""

    __tablename__ = "family_history_entries"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )
    relationship_code: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(15))  # "en_vida" | "fallecido"
    conditions: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class PersonalPathologicalHistory(_AnnullableMixin, AuditedMixin, Base):
    """Antecedentes personales patologicos: una fila por encounter (regla 6).
    `diseases` es un JSONB {codigo: {"present": bool, "evolution": str|None}}
    validado contra el catalogo "pathological_condition"."""

    __tablename__ = "personal_pathological_histories"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    dolor_masticar: Mapped[bool] = mapped_column(Boolean, default=False)
    sensibilidad_frio: Mapped[bool] = mapped_column(Boolean, default=False)
    sensibilidad_calor: Mapped[bool] = mapped_column(Boolean, default=False)
    sensibilidad_dulce: Mapped[bool] = mapped_column(Boolean, default=False)
    sensibilidad_localizacion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sangrado_encias: Mapped[str] = mapped_column(String(20), default="nunca")
    dolor_cepillado: Mapped[bool] = mapped_column(Boolean, default=False)
    aftas_ulceras: Mapped[bool] = mapped_column(Boolean, default=False)
    perdida_piezas: Mapped[bool] = mapped_column(Boolean, default=False)
    perdida_piezas_causa: Mapped[str | None] = mapped_column(String(300), nullable=True)
    anestesia_previa: Mapped[bool] = mapped_column(Boolean, default=False)
    extracciones: Mapped[bool] = mapped_column(Boolean, default=False)
    extracciones_texto: Mapped[str | None] = mapped_column(String(300), nullable=True)
    complicaciones_operatorias: Mapped[bool] = mapped_column(Boolean, default=False)
    complicaciones_operatorias_texto: Mapped[str | None] = mapped_column(String(300), nullable=True)
    traumatismo_dental: Mapped[bool] = mapped_column(Boolean, default=False)
    traumatismo_dental_texto: Mapped[str | None] = mapped_column(String(300), nullable=True)
    infecciones_dentales: Mapped[bool] = mapped_column(Boolean, default=False)
    infecciones_dentales_texto: Mapped[str | None] = mapped_column(String(300), nullable=True)
    estres: Mapped[bool] = mapped_column(Boolean, default=False)
    estres_texto: Mapped[str | None] = mapped_column(String(300), nullable=True)
    hospitalizacion_emergencia: Mapped[bool] = mapped_column(Boolean, default=False)
    hospitalizacion_emergencia_texto: Mapped[str | None] = mapped_column(String(300), nullable=True)
    infecciones_frecuentes: Mapped[bool] = mapped_column(Boolean, default=False)
    infecciones_frecuentes_zona: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tiempo_evolucion: Mapped[str | None] = mapped_column(String(200), nullable=True)
    diseases: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class PersonalNonPathologicalHistory(_AnnullableMixin, AuditedMixin, Base):
    """Antecedentes personales no patologicos: una fila por encounter (regla 6)."""

    __tablename__ = "personal_non_pathological_histories"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    comidas_dia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calidad_alimentacion: Mapped[str | None] = mapped_column(String(10), nullable=True)
    agua_litros_dia: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    trastornos_sueno: Mapped[bool] = mapped_column(Boolean, default=False)
    trastornos_sueno_texto: Mapped[str | None] = mapped_column(String(300), nullable=True)
    cepillados_dia: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hilo_dental: Mapped[bool] = mapped_column(Boolean, default=False)
    enjuague_bucal: Mapped[bool] = mapped_column(Boolean, default=False)
    deportes: Mapped[bool] = mapped_column(Boolean, default=False)
    deportes_cual: Mapped[str | None] = mapped_column(String(200), nullable=True)
    derechohabiencia: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Corrección Fase A: ya no es un catalogo cerrado (soltero/casado/concubinato) --
    # el formulario ofrece esas opciones mas "Otro" con texto libre, por eso el
    # campo es texto libre validado solo por longitud (ver schemas.py).
    estado_civil: Mapped[str | None] = mapped_column(String(60), nullable=True)
    medicamentos_suplementos: Mapped[bool] = mapped_column(Boolean, default=False)
    medicamentos_controlados: Mapped[bool] = mapped_column(Boolean, default=False)
    medicamentos_texto: Mapped[str | None] = mapped_column(String(300), nullable=True)
    servicios_basicos: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    adicciones: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


class SystemsReviewEntry(_AnnullableMixin, AuditedMixin, Base):
    """Interrogatorio por aparatos y sistemas: una fila por encounter (regla 6).
    Cada aparato es un JSONB {codigo_padecimiento: {"present": bool,
    "evolution": str|None}}, validado contra el catalogo
    "systems_review_finding" (filtrado por extra.system)."""

    __tablename__ = "systems_review_entries"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )

    hematologico: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    cardiovascular: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    neurologico: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    endocrino: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    respiratorio: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    genitourinario: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    reproductor_masculino: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    reproductor_femenino: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")
