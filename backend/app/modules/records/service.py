import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import AppError
from app.core.storage import StorageBackend
from app.modules.catalogs import service as catalogs_service
from app.modules.documents.pdf_header import get_pdf_header_info
from app.modules.odontogram import service as odontogram_service
from app.modules.patients.models import Patient
from app.modules.patients.rules import calculate_age
from app.modules.records import rules
from app.modules.records.models import (
    Allergy,
    FamilyHistoryEntry,
    MedicalHistory,
    Medication,
    PersonalNonPathologicalHistory,
    PersonalPathologicalHistory,
    SystemsReviewEntry,
    VitalSigns,
)
from app.modules.records.pdf import GeneralHistoryPdfData, build_general_history_pdf
from app.modules.records.schemas import (
    AllergyCreateRequest,
    AnnulRequest,
    FamilyHistoryEntryCreateRequest,
    MedicalHistoryCreateRequest,
    MedicationCreateRequest,
    PersonalNonPathologicalHistoryCreateRequest,
    PersonalPathologicalHistoryCreateRequest,
    SystemsReviewEntryCreateRequest,
    VitalSignsCreateRequest,
)


async def _get_patient_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> Patient:
    patient = await db.get(Patient, patient_id)
    if patient is None or patient.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Paciente no encontrado", status_code=404)
    return patient


async def list_history(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[MedicalHistory]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(MedicalHistory)
        .where(MedicalHistory.clinic_id == clinic_id, MedicalHistory.patient_id == patient_id)
        .order_by(MedicalHistory.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_history(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: MedicalHistoryCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> MedicalHistory:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    # B1 (Parte B, Fase 12.2): "Categorias de antecedentes" ya no es un Literal fijo --
    # valida contra el catalogo administrable de la sucursal.
    categories = await catalogs_service.get_active_codes(
        db, clinic_id=clinic_id, catalog_type="history_category"
    )
    if data.category not in categories:
        raise AppError(
            "INVALID_HISTORY_CATEGORY",
            "La categoria de antecedente no existe o esta desactivada en esta sucursal",
            status_code=400,
        )

    item = MedicalHistory(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        category=data.category,
        text=data.text,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="records.history_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="medical_history",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id), "category": data.category},
    )
    await db.commit()
    return item


async def annul_history(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> MedicalHistory:
    item = await db.get(MedicalHistory, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Antecedente no encontrado", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="records.history_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="medical_history",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


async def list_allergies(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[Allergy]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(Allergy)
        .where(Allergy.clinic_id == clinic_id, Allergy.patient_id == patient_id)
        .order_by(Allergy.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_allergy(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: AllergyCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> Allergy:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    item = Allergy(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        substance=data.substance,
        reaction=data.reaction,
        severity=data.severity,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="records.allergy_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="allergy",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id), "substance": data.substance},
    )
    await db.commit()
    return item


async def annul_allergy(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> Allergy:
    item = await db.get(Allergy, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Alergia no encontrada", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="records.allergy_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="allergy",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


async def list_medications(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[Medication]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(Medication)
        .where(Medication.clinic_id == clinic_id, Medication.patient_id == patient_id)
        .order_by(Medication.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_medication(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: MedicationCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> Medication:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    item = Medication(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        name=data.name,
        dose=data.dose,
        frequency=data.frequency,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="records.medication_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="medication",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id), "name": data.name},
    )
    await db.commit()
    return item


async def annul_medication(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> Medication:
    item = await db.get(Medication, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Medicamento no encontrado", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="records.medication_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="medication",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


async def list_vital_signs(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[VitalSigns]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(VitalSigns)
        .where(VitalSigns.clinic_id == clinic_id, VitalSigns.patient_id == patient_id)
        .order_by(VitalSigns.recorded_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_vital_signs(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: VitalSignsCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> VitalSigns:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    item = VitalSigns(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        recorded_at=datetime.now(UTC),
        bp_systolic=data.bp_systolic,
        bp_diastolic=data.bp_diastolic,
        heart_rate=data.heart_rate,
        temperature=data.temperature,
        height_m=data.height_m,
        weight_kg=data.weight_kg,
        spo2=data.spo2,
        glucose_index=data.glucose_index,
        glucose_timing=data.glucose_timing,
        patient_attitude=data.patient_attitude,
        asa_classification=data.asa_classification,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# Fase A (rediseno del expediente, docs/clinica): Historia Clinica General.
# --------------------------------------------------------------------------------


async def list_family_history(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[FamilyHistoryEntry]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(FamilyHistoryEntry)
        .where(
            FamilyHistoryEntry.clinic_id == clinic_id, FamilyHistoryEntry.patient_id == patient_id
        )
        .order_by(FamilyHistoryEntry.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def _check_codes_against_catalog(
    db: AsyncSession, *, clinic_id: uuid.UUID, catalog_type: str, codes: list[str], error_code: str
) -> None:
    if not codes:
        return
    active_codes = await catalogs_service.get_active_codes(
        db, clinic_id=clinic_id, catalog_type=catalog_type
    )
    unknown = sorted(set(codes) - active_codes)
    if unknown:
        raise AppError(
            error_code,
            f"Codigo(s) no reconocido(s) en el catalogo '{catalog_type}': {', '.join(unknown)}",
            status_code=400,
        )


async def create_family_history_entry(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: FamilyHistoryEntryCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> FamilyHistoryEntry:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    await _check_codes_against_catalog(
        db,
        clinic_id=clinic_id,
        catalog_type="family_relationship",
        codes=[data.relationship_code],
        error_code="INVALID_FAMILY_RELATIONSHIP",
    )
    await _check_codes_against_catalog(
        db,
        clinic_id=clinic_id,
        catalog_type="family_condition",
        codes=list(data.conditions.keys()),
        error_code="INVALID_FAMILY_CONDITION",
    )

    item = FamilyHistoryEntry(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        relationship_code=data.relationship_code,
        status=data.status,
        conditions=data.conditions,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="records.family_history_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="family_history_entry",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id), "relationship_code": data.relationship_code},
    )
    await db.commit()
    return item


async def annul_family_history_entry(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> FamilyHistoryEntry:
    item = await db.get(FamilyHistoryEntry, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Antecedente heredofamiliar no encontrado", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="records.family_history_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="family_history_entry",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


async def list_pathological_history(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[PersonalPathologicalHistory]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(PersonalPathologicalHistory)
        .where(
            PersonalPathologicalHistory.clinic_id == clinic_id,
            PersonalPathologicalHistory.patient_id == patient_id,
        )
        .order_by(PersonalPathologicalHistory.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_pathological_history(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: PersonalPathologicalHistoryCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> PersonalPathologicalHistory:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    await _check_codes_against_catalog(
        db,
        clinic_id=clinic_id,
        catalog_type="pathological_condition",
        codes=list(data.diseases.keys()),
        error_code="INVALID_PATHOLOGICAL_CONDITION",
    )

    item = PersonalPathologicalHistory(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        dolor_masticar=data.dolor_masticar,
        sensibilidad_frio=data.sensibilidad_frio,
        sensibilidad_calor=data.sensibilidad_calor,
        sensibilidad_dulce=data.sensibilidad_dulce,
        sensibilidad_localizacion=data.sensibilidad_localizacion,
        sangrado_encias=data.sangrado_encias,
        dolor_cepillado=data.dolor_cepillado,
        aftas_ulceras=data.aftas_ulceras,
        perdida_piezas=data.perdida_piezas,
        perdida_piezas_causa=data.perdida_piezas_causa,
        anestesia_previa=data.anestesia_previa,
        extracciones=data.extracciones,
        extracciones_texto=data.extracciones_texto,
        complicaciones_operatorias=data.complicaciones_operatorias,
        complicaciones_operatorias_texto=data.complicaciones_operatorias_texto,
        traumatismo_dental=data.traumatismo_dental,
        traumatismo_dental_texto=data.traumatismo_dental_texto,
        infecciones_dentales=data.infecciones_dentales,
        infecciones_dentales_texto=data.infecciones_dentales_texto,
        estres=data.estres,
        estres_texto=data.estres_texto,
        hospitalizacion_emergencia=data.hospitalizacion_emergencia,
        hospitalizacion_emergencia_texto=data.hospitalizacion_emergencia_texto,
        infecciones_frecuentes=data.infecciones_frecuentes,
        infecciones_frecuentes_zona=data.infecciones_frecuentes_zona,
        tiempo_evolucion=data.tiempo_evolucion,
        diseases=data.diseases,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="records.pathological_history_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="personal_pathological_history",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_pathological_history(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> PersonalPathologicalHistory:
    item = await db.get(PersonalPathologicalHistory, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError(
            "NOT_FOUND", "Antecedente patologico personal no encontrado", status_code=404
        )
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="records.pathological_history_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="personal_pathological_history",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


async def list_non_pathological_history(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[PersonalNonPathologicalHistory]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(PersonalNonPathologicalHistory)
        .where(
            PersonalNonPathologicalHistory.clinic_id == clinic_id,
            PersonalNonPathologicalHistory.patient_id == patient_id,
        )
        .order_by(PersonalNonPathologicalHistory.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_non_pathological_history(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: PersonalNonPathologicalHistoryCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> PersonalNonPathologicalHistory:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)

    item = PersonalNonPathologicalHistory(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        comidas_dia=data.comidas_dia,
        calidad_alimentacion=data.calidad_alimentacion,
        agua_litros_dia=data.agua_litros_dia,
        trastornos_sueno=data.trastornos_sueno,
        trastornos_sueno_texto=data.trastornos_sueno_texto,
        cepillados_dia=data.cepillados_dia,
        hilo_dental=data.hilo_dental,
        enjuague_bucal=data.enjuague_bucal,
        deportes=data.deportes,
        deportes_cual=data.deportes_cual,
        derechohabiencia=data.derechohabiencia,
        estado_civil=data.estado_civil,
        medicamentos_suplementos=data.medicamentos_suplementos,
        medicamentos_controlados=data.medicamentos_controlados,
        medicamentos_texto=data.medicamentos_texto,
        servicios_basicos=data.servicios_basicos,
        adicciones=data.adicciones,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="records.non_pathological_history_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="personal_non_pathological_history",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_non_pathological_history(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> PersonalNonPathologicalHistory:
    item = await db.get(PersonalNonPathologicalHistory, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError(
            "NOT_FOUND", "Antecedente no patologico personal no encontrado", status_code=404
        )
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="records.non_pathological_history_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="personal_non_pathological_history",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


async def list_systems_review(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[SystemsReviewEntry]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(SystemsReviewEntry)
        .where(
            SystemsReviewEntry.clinic_id == clinic_id, SystemsReviewEntry.patient_id == patient_id
        )
        .order_by(SystemsReviewEntry.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_systems_review(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: SystemsReviewEntryCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> SystemsReviewEntry:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    for system in rules.SYSTEMS_REVIEW_SYSTEMS:
        await _check_codes_against_catalog(
            db,
            clinic_id=clinic_id,
            catalog_type="systems_review_finding",
            codes=list(getattr(data, system).keys()),
            error_code="INVALID_SYSTEMS_REVIEW_FINDING",
        )

    item = SystemsReviewEntry(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        hematologico=data.hematologico,
        cardiovascular=data.cardiovascular,
        neurologico=data.neurologico,
        endocrino=data.endocrino,
        respiratorio=data.respiratorio,
        genitourinario=data.genitourinario,
        reproductor_masculino=data.reproductor_masculino,
        reproductor_femenino=data.reproductor_femenino,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="records.systems_review_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="systems_review_entry",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_systems_review(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> SystemsReviewEntry:
    item = await db.get(SystemsReviewEntry, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError(
            "NOT_FOUND", "Interrogatorio por aparatos y sistemas no encontrado", status_code=404
        )
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="records.systems_review_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="systems_review_entry",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


def _annul(
    item: (
        Allergy
        | Medication
        | MedicalHistory
        | FamilyHistoryEntry
        | PersonalPathologicalHistory
        | PersonalNonPathologicalHistory
        | SystemsReviewEntry
    ),
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> None:
    item.is_active = False
    item.annul_reason = data.reason
    item.annulled_by = actor_id
    item.annulled_at = datetime.now(UTC)


async def _alert_keyword_catalog(
    db: AsyncSession, *, clinic_id: uuid.UUID, catalog_type: str
) -> dict[str, str]:
    """B1 (Parte B, Fase 12.2): "Palabras clave de alerta" ya no son los diccionarios
    fijos `CONDITION_ALERT_KEYWORDS`/`MEDICATION_ALERT_KEYWORDS` -- viven en el
    catalogo administrable de la sucursal (campo `extra.alert_label`)."""
    items = await catalogs_service.list_items(db, clinic_id=clinic_id, catalog_type=catalog_type)
    return {item.code: str(item.extra.get("alert_label", item.name)) for item in items}


async def get_patient_alerts(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[str]:
    """Alertas clinicas derivadas (regla 8 de CLAUDE.md): se calculan, no se guardan."""
    alerts: list[str] = []

    allergy_stmt = select(Allergy).where(
        Allergy.clinic_id == clinic_id,
        Allergy.patient_id == patient_id,
        Allergy.is_active.is_(True),
    )
    for allergy in (await db.execute(allergy_stmt)).scalars().all():
        alerts.append(rules.allergy_alert(allergy.substance, allergy.severity))

    medication_keywords = await _alert_keyword_catalog(
        db, clinic_id=clinic_id, catalog_type="medication_alert_keyword"
    )
    medication_stmt = select(Medication).where(
        Medication.clinic_id == clinic_id,
        Medication.patient_id == patient_id,
        Medication.is_active.is_(True),
    )
    for medication in (await db.execute(medication_stmt)).scalars().all():
        alerts.extend(rules.match_alert_keywords(medication.name, medication_keywords))

    condition_keywords = await _alert_keyword_catalog(
        db, clinic_id=clinic_id, catalog_type="condition_alert_keyword"
    )
    history_stmt = select(MedicalHistory).where(
        MedicalHistory.clinic_id == clinic_id,
        MedicalHistory.patient_id == patient_id,
        MedicalHistory.is_active.is_(True),
    )
    for history in (await db.execute(history_stmt)).scalars().all():
        alerts.extend(rules.match_alert_keywords(history.text, condition_keywords))

    # Fase A / regla 8 de CLAUDE.md: las alertas criticas tambien salen de los
    # antecedentes patologicos personales estructurados (diseases marcados
    # "present" + textos libres), no solo del texto libre de MedicalHistory.
    pathological_stmt = select(PersonalPathologicalHistory).where(
        PersonalPathologicalHistory.clinic_id == clinic_id,
        PersonalPathologicalHistory.patient_id == patient_id,
        PersonalPathologicalHistory.is_active.is_(True),
    )
    for item in (await db.execute(pathological_stmt)).scalars().all():
        text = rules.pathological_history_alert_text(
            item.diseases,
            [
                item.sensibilidad_localizacion,
                item.perdida_piezas_causa,
                item.extracciones_texto,
                item.complicaciones_operatorias_texto,
                item.traumatismo_dental_texto,
                item.infecciones_dentales_texto,
                item.hospitalizacion_emergencia_texto,
            ],
        )
        alerts.extend(rules.match_alert_keywords(text, condition_keywords))

    seen: set[str] = set()
    unique_alerts = []
    for alert in alerts:
        if alert not in seen:
            seen.add(alert)
            unique_alerts.append(alert)
    return unique_alerts


_SEX_LABELS: dict[str | None, str] = {
    "F": "Femenino",
    "M": "Masculino",
    "X": "Otro",
    None: "No especificado",
}


async def _catalog_label_map(
    db: AsyncSession, *, clinic_id: uuid.UUID, catalog_type: str
) -> dict[str, str]:
    items = await catalogs_service.list_items(
        db, clinic_id=clinic_id, catalog_type=catalog_type, include_inactive=True
    )
    return {item.code: item.name for item in items}


async def generate_general_history_pdf(
    db: AsyncSession,
    storage: StorageBackend,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> bytes:
    """Fase A (rediseno del expediente, docs/clinica): PDF de la Historia
    Clinica General completa -- paciente + heredofamiliares + antecedentes
    personales patologicos/no patologicos + aparatos y sistemas +
    alergias/medicamentos/signos vitales ya existentes + odontograma de
    diagnostico actual tal cual existe hoy (SIN rediseñarlo, eso es la Fase B).
    """
    patient = await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    header = await get_pdf_header_info(db, storage, clinic_id=clinic_id)

    relationship_labels = await _catalog_label_map(
        db, clinic_id=clinic_id, catalog_type="family_relationship"
    )
    family_condition_labels = await _catalog_label_map(
        db, clinic_id=clinic_id, catalog_type="family_condition"
    )
    pathological_labels = await _catalog_label_map(
        db, clinic_id=clinic_id, catalog_type="pathological_condition"
    )
    systems_finding_labels = await _catalog_label_map(
        db, clinic_id=clinic_id, catalog_type="systems_review_finding"
    )
    odontogram_labels = await _catalog_label_map(
        db, clinic_id=clinic_id, catalog_type="odontogram_finding"
    )

    family_history = [
        item
        for item in await list_family_history(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    pathological = [
        item
        for item in await list_pathological_history(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    non_pathological = [
        item
        for item in await list_non_pathological_history(
            db, clinic_id=clinic_id, patient_id=patient_id
        )
        if item.is_active
    ]
    systems_review = [
        item
        for item in await list_systems_review(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    allergies = [
        item
        for item in await list_allergies(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    medications = [
        item
        for item in await list_medications(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    vital_signs = await list_vital_signs(db, clinic_id=clinic_id, patient_id=patient_id)
    odontogram_findings = await odontogram_service.get_current_odontogram(
        db, clinic_id=clinic_id, patient_id=patient_id
    )

    def _system_rows(entry: SystemsReviewEntry) -> list[str]:
        rows: list[str] = []
        for system in rules.SYSTEMS_REVIEW_SYSTEMS:
            findings: dict[str, dict[str, object]] = getattr(entry, system)
            present = [
                systems_finding_labels.get(code, code)
                for code, info in findings.items()
                if isinstance(info, dict) and info.get("present")
            ]
            if present:
                rows.append(f"{system}: {', '.join(present)}")
        if entry.reproductor_masculino:
            rows.append(f"Reproductor masculino: {entry.reproductor_masculino}")
        if entry.reproductor_femenino:
            rows.append(f"Reproductor femenino: {entry.reproductor_femenino}")
        return rows

    data = GeneralHistoryPdfData(
        header=header,
        date_label=datetime.now(UTC).strftime("%d/%m/%Y"),
        patient_full_name=patient.full_name,
        patient_expediente_number=patient.expediente_number,
        patient_age=calculate_age(patient.date_of_birth),
        patient_sex_label=_SEX_LABELS.get(patient.sex, "No especificado"),
        patient_extra_fields={
            k: v
            for k, v in {
                "Lugar de nacimiento": patient.birth_place,
                "Tipo de sangre": patient.blood_type,
                "Escolaridad": patient.education_level,
                "Ocupacion": patient.occupation,
                "Estado civil": patient.marital_status,
                "Religion": patient.religion,
            }.items()
            if v
        },
        family_history_rows=[
            {
                "relationship": relationship_labels.get(
                    item.relationship_code, item.relationship_code
                ),
                "status": item.status,
                "conditions": [
                    family_condition_labels.get(code, code)
                    for code, marked in item.conditions.items()
                    if marked
                ],
            }
            for item in family_history
        ],
        pathological_rows=[
            f"{pathological_labels.get(code, code)}"
            + (f" (evolucion: {info.get('evolution')})" if info.get("evolution") else "")
            for item in pathological
            for code, info in item.diseases.items()
            if isinstance(info, dict) and info.get("present")
        ],
        non_pathological_rows=[
            f"Alimentacion: {item.comidas_dia or '-'} comidas/dia, calidad "
            f"{item.calidad_alimentacion or '-'}; higiene bucal: "
            f"{item.cepillados_dia or '-'} cepillados/dia"
            f"{', hilo dental' if item.hilo_dental else ''}"
            f"{', enjuague bucal' if item.enjuague_bucal else ''}; "
            f"estado civil: {item.estado_civil or '-'}; derechohabiencia: "
            f"{item.derechohabiencia or '-'}"
            for item in non_pathological
        ],
        systems_review_rows=[row for entry in systems_review for row in _system_rows(entry)],
        allergy_rows=[
            f"{item.substance} ({item.severity})"
            + (f" -- {item.reaction}" if item.reaction else "")
            for item in allergies
        ],
        medication_rows=[
            f"{item.name}"
            + (f" {item.dose}" if item.dose else "")
            + (f", {item.frequency}" if item.frequency else "")
            for item in medications
        ],
        vital_signs_rows=[
            f"{vs.recorded_at.strftime('%d/%m/%Y')}: "
            f"TA {vs.bp_systolic or '-'}/{vs.bp_diastolic or '-'}, "
            f"FC {vs.heart_rate or '-'}, Temp {vs.temperature or '-'}, SpO2 {vs.spo2 or '-'}, "
            f"IMC {rules.body_mass_index(vs.height_m, vs.weight_kg) or '-'}"
            for vs in vital_signs
        ],
        odontogram_rows=[
            f"Pieza {tf.tooth_fdi}"
            + (f" ({tf.surface})" if tf.surface else "")
            + f": {odontogram_labels.get(tf.finding_code, tf.finding_code)}"
            for tf in odontogram_findings
        ],
    )

    pdf_bytes = build_general_history_pdf(data)

    await audit_service.log(
        db,
        action="records.general_history_pdf_read",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="patient",
        entity_id=str(patient_id),
    )
    await db.commit()
    return pdf_bytes
