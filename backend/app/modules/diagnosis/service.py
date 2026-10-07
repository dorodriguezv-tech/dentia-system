import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import AppError
from app.modules.catalogs import service as catalogs_service
from app.modules.diagnosis.models import Diagnosis
from app.modules.diagnosis.schemas import AnnulRequest, DiagnosisCreateRequest
from app.modules.encounters.models import Encounter
from app.modules.odontogram import rules as odontogram_rules
from app.modules.patients.models import Patient


async def _get_patient_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> Patient:
    patient = await db.get(Patient, patient_id)
    if patient is None or patient.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Paciente no encontrado", status_code=404)
    return patient


async def _get_encounter_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, encounter_id: uuid.UUID
) -> Encounter:
    encounter = await db.get(Encounter, encounter_id)
    if encounter is None or encounter.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Atencion no encontrada", status_code=404)
    return encounter


def _validate_tooth_surface(tooth_fdi: int | None, surface: str | None) -> None:
    if tooth_fdi is None:
        if surface is not None:
            raise AppError(
                "INVALID_SURFACE", "No se puede indicar superficie sin pieza", status_code=422
            )
        return
    if not odontogram_rules.is_valid_tooth(tooth_fdi):
        raise AppError("INVALID_TOOTH", f"Pieza FDI invalida: {tooth_fdi}", status_code=422)
    if not odontogram_rules.is_valid_surface_for_tooth(tooth_fdi, surface):
        raise AppError(
            "INVALID_SURFACE",
            f"La superficie {surface} no es valida para la pieza {tooth_fdi}",
            status_code=422,
        )


async def create_diagnosis(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: DiagnosisCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> Diagnosis:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    await _get_encounter_in_clinic(db, clinic_id=clinic_id, encounter_id=data.encounter_id)
    _validate_tooth_surface(data.tooth_fdi, data.surface)

    # B1 (Parte B, Fase 12.2): "Diagnosticos" ya no es un Literal fijo -- el codigo
    # sigue siendo opcional (el texto del diagnostico siempre es libre), pero si se
    # manda, valida contra el catalogo administrable de la sucursal.
    if data.code is not None:
        codes = await catalogs_service.get_active_codes(
            db, clinic_id=clinic_id, catalog_type="diagnosis"
        )
        if data.code not in codes:
            raise AppError(
                "INVALID_DIAGNOSIS_CODE",
                "El codigo de diagnostico no existe o esta desactivado en esta sucursal",
                status_code=400,
            )

    item = Diagnosis(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        professional_id=actor_id,
        tooth_fdi=data.tooth_fdi,
        surface=data.surface,
        code=data.code,
        text=data.text,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="diagnosis.created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="diagnosis",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id), "code": data.code, "tooth_fdi": data.tooth_fdi},
    )
    await db.commit()
    return item


async def list_diagnoses(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[Diagnosis]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(Diagnosis)
        .where(Diagnosis.clinic_id == clinic_id, Diagnosis.patient_id == patient_id)
        .order_by(Diagnosis.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def annul_diagnosis(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> Diagnosis:
    item = await db.get(Diagnosis, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Diagnostico no encontrado", status_code=404)

    item.is_active = False
    item.annul_reason = data.reason
    item.annulled_by = actor_id
    item.annulled_at = datetime.now(UTC)

    await audit_service.log(
        db,
        action="diagnosis.annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="diagnosis",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item
