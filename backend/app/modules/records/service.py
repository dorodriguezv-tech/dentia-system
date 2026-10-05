import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import AppError
from app.modules.patients.models import Patient
from app.modules.records import rules
from app.modules.records.models import Allergy, MedicalHistory, Medication, VitalSigns
from app.modules.records.schemas import (
    AllergyCreateRequest,
    AnnulRequest,
    MedicalHistoryCreateRequest,
    MedicationCreateRequest,
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
) -> MedicalHistory:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    item = MedicalHistory(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        category=data.category,
        text=data.text,
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
) -> Allergy:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    item = Allergy(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        substance=data.substance,
        reaction=data.reaction,
        severity=data.severity,
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
) -> Medication:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    item = Medication(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        name=data.name,
        dose=data.dose,
        frequency=data.frequency,
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
        created_by=actor_id,
    )
    db.add(item)
    await db.commit()
    return item


def _annul(
    item: Allergy | Medication | MedicalHistory, data: AnnulRequest, actor_id: uuid.UUID
) -> None:
    item.is_active = False
    item.annul_reason = data.reason
    item.annulled_by = actor_id
    item.annulled_at = datetime.now(UTC)


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

    medication_stmt = select(Medication).where(
        Medication.clinic_id == clinic_id,
        Medication.patient_id == patient_id,
        Medication.is_active.is_(True),
    )
    for medication in (await db.execute(medication_stmt)).scalars().all():
        alerts.extend(rules.match_alert_keywords(medication.name, rules.MEDICATION_ALERT_KEYWORDS))

    history_stmt = select(MedicalHistory).where(
        MedicalHistory.clinic_id == clinic_id,
        MedicalHistory.patient_id == patient_id,
        MedicalHistory.is_active.is_(True),
    )
    for history in (await db.execute(history_stmt)).scalars().all():
        alerts.extend(rules.match_alert_keywords(history.text, rules.CONDITION_ALERT_KEYWORDS))

    seen: set[str] = set()
    unique_alerts = []
    for alert in alerts:
        if alert not in seen:
            seen.add(alert)
            unique_alerts.append(alert)
    return unique_alerts
