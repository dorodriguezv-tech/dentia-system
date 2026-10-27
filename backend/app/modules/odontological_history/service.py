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
from app.modules.odontological_history import rules
from app.modules.odontological_history.models import (
    OdontogramDiagnosisDetail,
    OdontologicalExam,
    ParallelometerAnalysis,
    PeriodontalAnamnesis,
    RadiographicAnalysis,
    RemovablePartialDentureDesign,
    ToothDiagnosisEntry,
    ToothTreatmentPlanEntry,
)
from app.modules.odontological_history.pdf import (
    OdontologicalHistoryPdfData,
    build_odontological_history_pdf,
)
from app.modules.odontological_history.schemas import (
    AnnulRequest,
    OdontogramDiagnosisDetailCreateRequest,
    OdontologicalExamCreateRequest,
    ParallelometerAnalysisCreateRequest,
    PeriodontalAnamnesisCreateRequest,
    RadiographicAnalysisCreateRequest,
    RemovablePartialDentureDesignCreateRequest,
    ToothDiagnosisEntryCreateRequest,
    ToothTreatmentPlanEntryCreateRequest,
)
from app.modules.patients.models import Patient

AnnullableEntry = (
    OdontologicalExam
    | PeriodontalAnamnesis
    | RadiographicAnalysis
    | OdontogramDiagnosisDetail
    | ParallelometerAnalysis
    | RemovablePartialDentureDesign
    | ToothDiagnosisEntry
    | ToothTreatmentPlanEntry
)


async def _get_patient_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> Patient:
    patient = await db.get(Patient, patient_id)
    if patient is None or patient.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Paciente no encontrado", status_code=404)
    return patient


def _annul(item: AnnullableEntry, data: AnnulRequest, actor_id: uuid.UUID) -> None:
    item.is_active = False
    item.annul_reason = data.reason
    item.annulled_by = actor_id
    item.annulled_at = datetime.now(UTC)


async def _check_tooth_codes(codes: list[str], *, include_temporary: bool = False) -> None:
    """Valida piezas FDI. Por defecto solo permanentes (diagnostico por organo
    dental y analisis de protesis fija -- la especificacion no las aplica a
    piezas temporales). `include_temporary=True` (plan de tratamiento, tambien
    usado por la Historia Pediatrica -- Fase E) amplia la validacion a
    `rules.TOOTH_FDI_ALL_CODES` (permanentes + temporales)."""
    is_valid = (
        rules.is_valid_tooth_code if include_temporary else rules.is_valid_permanent_tooth_code
    )
    unknown = sorted(code for code in codes if not is_valid(code))
    if unknown:
        raise AppError(
            "INVALID_TOOTH",
            f"Pieza(s) FDI invalida(s): {', '.join(unknown)}",
            status_code=422,
        )


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


# --------------------------------------------------------------------------------
# 1. Exploracion cabeza/cuello + biotipo facial + ATM + tejidos blandos.
# --------------------------------------------------------------------------------


async def list_odontological_exams(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[OdontologicalExam]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(OdontologicalExam)
        .where(OdontologicalExam.clinic_id == clinic_id, OdontologicalExam.patient_id == patient_id)
        .order_by(OdontologicalExam.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_odontological_exam(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: OdontologicalExamCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> OdontologicalExam:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    await _check_codes_against_catalog(
        db,
        clinic_id=clinic_id,
        catalog_type="skull_type",
        codes=[data.skull_type] if data.skull_type else [],
        error_code="INVALID_SKULL_TYPE",
    )
    await _check_codes_against_catalog(
        db,
        clinic_id=clinic_id,
        catalog_type="facial_biotype",
        codes=[data.facial_biotype] if data.facial_biotype else [],
        error_code="INVALID_FACIAL_BIOTYPE",
    )

    item = OdontologicalExam(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        skull_type=data.skull_type,
        facial_biotype=data.facial_biotype,
        facial_biotype_observations=data.facial_biotype_observations,
        apertura_conservada_mm=data.apertura_conservada_mm,
        apertura_limitada_mm=data.apertura_limitada_mm,
        chasquidos_derecho=data.chasquidos_derecho,
        crepitacion_derecho=data.crepitacion_derecho,
        chasquidos_izquierdo=data.chasquidos_izquierdo,
        crepitacion_izquierdo=data.crepitacion_izquierdo,
        dolor_apertura_lateralidad=data.dolor_apertura_lateralidad,
        fatiga_dolor_muscular=data.fatiga_dolor_muscular,
        desviacion_apertura_cierre=data.desviacion_apertura_cierre,
        atm_observaciones=data.atm_observaciones,
        ganglios=data.ganglios,
        carrillos=data.carrillos,
        labios=data.labios,
        lengua=data.lengua,
        piso_boca=data.piso_boca,
        region_retromolar=data.region_retromolar,
        paladar_duro_blando=data.paladar_duro_blando,
        faringe=data.faringe,
        encia_libre_marginal=data.encia_libre_marginal,
        tejidos_blandos_observaciones=data.tejidos_blandos_observaciones,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="odontological_history.exam_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="odontological_exam",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_odontological_exam(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> OdontologicalExam:
    item = await db.get(OdontologicalExam, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Exploracion odontologica no encontrada", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="odontological_history.exam_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="odontological_exam",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 2. Anamnesis periodontal.
# --------------------------------------------------------------------------------


async def list_periodontal_anamneses(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[PeriodontalAnamnesis]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(PeriodontalAnamnesis)
        .where(
            PeriodontalAnamnesis.clinic_id == clinic_id,
            PeriodontalAnamnesis.patient_id == patient_id,
        )
        .order_by(PeriodontalAnamnesis.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_periodontal_anamnesis(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: PeriodontalAnamnesisCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> PeriodontalAnamnesis:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    await _check_codes_against_catalog(
        db,
        clinic_id=clinic_id,
        catalog_type="periodontal_anamnesis_question",
        codes=list(data.answers.keys()),
        error_code="INVALID_PERIODONTAL_ANAMNESIS_QUESTION",
    )

    item = PeriodontalAnamnesis(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        answers=dict(data.answers),
        cepillado_veces_dia=data.cepillado_veces_dia,
        cepillado_pasta=data.cepillado_pasta,
        insatisfaccion_motivo=data.insatisfaccion_motivo,
        tratamiento_medico_detalle=data.tratamiento_medico_detalle,
        medicamento_actual=data.medicamento_actual,
        cirugia_detalle=data.cirugia_detalle,
        hormonas_para_que=data.hormonas_para_que,
        habito_danino_cual=data.habito_danino_cual,
        fuma_cigarros_dia=data.fuma_cigarros_dia,
        alcohol_veces_semana=data.alcohol_veces_semana,
        ultimo_examen_odontologico=data.ultimo_examen_odontologico,
        salud_bucal_autopercibida=data.salud_bucal_autopercibida,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="odontological_history.periodontal_anamnesis_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="periodontal_anamnesis",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_periodontal_anamnesis(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> PeriodontalAnamnesis:
    item = await db.get(PeriodontalAnamnesis, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Anamnesis periodontal no encontrada", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="odontological_history.periodontal_anamnesis_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="periodontal_anamnesis",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 3. Auxiliares de diagnostico -- analisis radiografico.
# --------------------------------------------------------------------------------


async def list_radiographic_analyses(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[RadiographicAnalysis]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(RadiographicAnalysis)
        .where(
            RadiographicAnalysis.clinic_id == clinic_id,
            RadiographicAnalysis.patient_id == patient_id,
        )
        .order_by(RadiographicAnalysis.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_radiographic_analysis(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: RadiographicAnalysisCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> RadiographicAnalysis:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    unknown_types = sorted(set(data.findings.keys()) - set(rules.RADIOGRAPHIC_FINDING_TYPES))
    if unknown_types:
        raise AppError(
            "INVALID_RADIOGRAPHIC_FINDING_TYPE",
            f"Tipo(s) de hallazgo radiografico invalido(s): {', '.join(unknown_types)}",
            status_code=400,
        )

    item = RadiographicAnalysis(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        findings={key: value.model_dump() for key, value in data.findings.items()},
        anexos_nota=data.anexos_nota,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="odontological_history.radiographic_analysis_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="radiographic_analysis",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_radiographic_analysis(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> RadiographicAnalysis:
    item = await db.get(RadiographicAnalysis, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Analisis radiografico no encontrado", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="odontological_history.radiographic_analysis_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="radiographic_analysis",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 4. Odontograma de diagnostico -- datos complementarios.
# --------------------------------------------------------------------------------


async def list_odontogram_diagnosis_details(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[OdontogramDiagnosisDetail]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(OdontogramDiagnosisDetail)
        .where(
            OdontogramDiagnosisDetail.clinic_id == clinic_id,
            OdontogramDiagnosisDetail.patient_id == patient_id,
        )
        .order_by(OdontogramDiagnosisDetail.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_odontogram_diagnosis_detail(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: OdontogramDiagnosisDetailCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> OdontogramDiagnosisDetail:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    await _check_tooth_codes([entry.tooth_fdi for entry in data.fixed_prosthesis_analysis])

    item = OdontogramDiagnosisDetail(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        edentulous_space_available=data.edentulous_space_available,
        edentulous_space_comments=data.edentulous_space_comments,
        kennedy_sup_class=data.kennedy_sup_class,
        kennedy_sup_modification=data.kennedy_sup_modification,
        kennedy_inf_class=data.kennedy_inf_class,
        kennedy_inf_modification=data.kennedy_inf_modification,
        fixed_prosthesis_analysis=[entry.model_dump() for entry in data.fixed_prosthesis_analysis],
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="odontological_history.odontogram_diagnosis_detail_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="odontogram_diagnosis_detail",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_odontogram_diagnosis_detail(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> OdontogramDiagnosisDetail:
    item = await db.get(OdontogramDiagnosisDetail, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError(
            "NOT_FOUND", "Dato complementario del odontograma no encontrado", status_code=404
        )
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="odontological_history.odontogram_diagnosis_detail_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="odontogram_diagnosis_detail",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 5. Analisis con paralelometro.
# --------------------------------------------------------------------------------


async def list_parallelometer_analyses(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[ParallelometerAnalysis]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(ParallelometerAnalysis)
        .where(
            ParallelometerAnalysis.clinic_id == clinic_id,
            ParallelometerAnalysis.patient_id == patient_id,
        )
        .order_by(ParallelometerAnalysis.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_parallelometer_analysis(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: ParallelometerAnalysisCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> ParallelometerAnalysis:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)

    item = ParallelometerAnalysis(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        entries=[entry.model_dump() for entry in data.entries],
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="odontological_history.parallelometer_analysis_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="parallelometer_analysis",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_parallelometer_analysis(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> ParallelometerAnalysis:
    item = await db.get(ParallelometerAnalysis, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Analisis con paralelometro no encontrado", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="odontological_history.parallelometer_analysis_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="parallelometer_analysis",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 6. Diseno de protesis parcial removible.
# --------------------------------------------------------------------------------


async def list_removable_partial_denture_designs(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[RemovablePartialDentureDesign]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(RemovablePartialDentureDesign)
        .where(
            RemovablePartialDentureDesign.clinic_id == clinic_id,
            RemovablePartialDentureDesign.patient_id == patient_id,
        )
        .order_by(RemovablePartialDentureDesign.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_removable_partial_denture_design(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: RemovablePartialDentureDesignCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> RemovablePartialDentureDesign:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)

    item = RemovablePartialDentureDesign(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        conector_mayor=data.conector_mayor,
        conector_menor=data.conector_menor,
        retenedores_directos=data.retenedores_directos,
        conectores_indirectos=data.conectores_indirectos,
        base_protesica=data.base_protesica,
        dientes_artificiales=data.dientes_artificiales,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="odontological_history.removable_partial_denture_design_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="removable_partial_denture_design",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_removable_partial_denture_design(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> RemovablePartialDentureDesign:
    item = await db.get(RemovablePartialDentureDesign, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError(
            "NOT_FOUND", "Diseno de protesis parcial removible no encontrado", status_code=404
        )
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="odontological_history.removable_partial_denture_design_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="removable_partial_denture_design",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 7. Diagnostico por organo dental.
# --------------------------------------------------------------------------------


async def list_tooth_diagnosis_entries(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[ToothDiagnosisEntry]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(ToothDiagnosisEntry)
        .where(
            ToothDiagnosisEntry.clinic_id == clinic_id,
            ToothDiagnosisEntry.patient_id == patient_id,
        )
        .order_by(ToothDiagnosisEntry.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_tooth_diagnosis_entry(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: ToothDiagnosisEntryCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> ToothDiagnosisEntry:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    await _check_tooth_codes(list(data.diagnoses.keys()))

    item = ToothDiagnosisEntry(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        diagnoses=dict(data.diagnoses),
        observaciones=data.observaciones,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="odontological_history.tooth_diagnosis_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="tooth_diagnosis_entry",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_tooth_diagnosis_entry(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> ToothDiagnosisEntry:
    item = await db.get(ToothDiagnosisEntry, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Diagnostico por organo dental no encontrado", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="odontological_history.tooth_diagnosis_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="tooth_diagnosis_entry",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 8. Plan de tratamiento por organo dental.
# --------------------------------------------------------------------------------


async def list_tooth_treatment_plan_entries(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[ToothTreatmentPlanEntry]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(ToothTreatmentPlanEntry)
        .where(
            ToothTreatmentPlanEntry.clinic_id == clinic_id,
            ToothTreatmentPlanEntry.patient_id == patient_id,
        )
        .order_by(ToothTreatmentPlanEntry.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_tooth_treatment_plan_entry(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: ToothTreatmentPlanEntryCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> ToothTreatmentPlanEntry:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    # Fase E: el plan de tratamiento por organo dental tambien se usa para el
    # plan pediatrico permanente/temporal, asi que acepta ambos tipos de pieza.
    await _check_tooth_codes(list(data.plans.keys()), include_temporary=True)

    item = ToothTreatmentPlanEntry(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        plans=dict(data.plans),
        observaciones=data.observaciones,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="odontological_history.tooth_treatment_plan_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="tooth_treatment_plan_entry",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_tooth_treatment_plan_entry(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> ToothTreatmentPlanEntry:
    item = await db.get(ToothTreatmentPlanEntry, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError(
            "NOT_FOUND", "Plan de tratamiento por organo dental no encontrado", status_code=404
        )
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="odontological_history.tooth_treatment_plan_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="tooth_treatment_plan_entry",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# PDF: GET /patients/{patient_id}/odontological-history/pdf
# --------------------------------------------------------------------------------


async def _catalog_label_map(
    db: AsyncSession, *, clinic_id: uuid.UUID, catalog_type: str
) -> dict[str, str]:
    items = await catalogs_service.list_items(
        db, clinic_id=clinic_id, catalog_type=catalog_type, include_inactive=True
    )
    return {item.code: item.name for item in items}


async def generate_odontological_history_pdf(
    db: AsyncSession,
    storage: StorageBackend,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> bytes:
    """Historia Clinica Odontologica completa en PDF (Fase C): odontograma de
    diagnostico actual (reutilizado tal cual de la Fase B) + las 8 secciones
    nuevas de esta fase. NO incluye periodontograma completo (sondeo por
    sitio, Fase G)."""
    patient = await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    header = await get_pdf_header_info(db, storage, clinic_id=clinic_id)

    skull_type_labels = await _catalog_label_map(db, clinic_id=clinic_id, catalog_type="skull_type")
    facial_biotype_labels = await _catalog_label_map(
        db, clinic_id=clinic_id, catalog_type="facial_biotype"
    )
    question_labels = await _catalog_label_map(
        db, clinic_id=clinic_id, catalog_type="periodontal_anamnesis_question"
    )
    odontogram_labels = await _catalog_label_map(
        db, clinic_id=clinic_id, catalog_type="odontogram_finding"
    )

    odontogram_findings = await odontogram_service.get_current_odontogram(
        db, clinic_id=clinic_id, patient_id=patient_id
    )
    exams = [
        item
        for item in await list_odontological_exams(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    anamneses = [
        item
        for item in await list_periodontal_anamneses(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    radiographic_analyses = [
        item
        for item in await list_radiographic_analyses(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    odontogram_details = [
        item
        for item in await list_odontogram_diagnosis_details(
            db, clinic_id=clinic_id, patient_id=patient_id
        )
        if item.is_active
    ]
    parallelometer_analyses = [
        item
        for item in await list_parallelometer_analyses(
            db, clinic_id=clinic_id, patient_id=patient_id
        )
        if item.is_active
    ]
    rpd_designs = [
        item
        for item in await list_removable_partial_denture_designs(
            db, clinic_id=clinic_id, patient_id=patient_id
        )
        if item.is_active
    ]
    tooth_diagnoses = [
        item
        for item in await list_tooth_diagnosis_entries(
            db, clinic_id=clinic_id, patient_id=patient_id
        )
        if item.is_active
    ]
    tooth_treatment_plans = [
        item
        for item in await list_tooth_treatment_plan_entries(
            db, clinic_id=clinic_id, patient_id=patient_id
        )
        if item.is_active
    ]

    def _exam_rows(item: OdontologicalExam) -> list[str]:
        skull_label = skull_type_labels.get(item.skull_type or "", item.skull_type)
        facial_label = facial_biotype_labels.get(item.facial_biotype or "", item.facial_biotype)
        rows = [
            f"Craneo: {skull_label}" if item.skull_type else None,
            f"Biotipo facial: {facial_label}" if item.facial_biotype else None,
            f"ATM -- apertura conservada: {item.apertura_conservada_mm or '-'} mm, "
            f"apertura limitada: {item.apertura_limitada_mm or '-'} mm",
        ]
        atm_findings = [
            label
            for flag, label in (
                (item.chasquidos_derecho, "chasquidos derecho"),
                (item.crepitacion_derecho, "crepitacion derecho"),
                (item.chasquidos_izquierdo, "chasquidos izquierdo"),
                (item.crepitacion_izquierdo, "crepitacion izquierdo"),
                (item.dolor_apertura_lateralidad, "dolor a la apertura/lateralidad"),
                (item.fatiga_dolor_muscular, "fatiga o dolor muscular"),
                (item.desviacion_apertura_cierre, "desviacion a la apertura/cierre"),
            )
            if flag
        ]
        if atm_findings:
            rows.append("ATM -- hallazgos: " + ", ".join(atm_findings))
        soft_tissue_pairs = [
            ("Ganglios", item.ganglios),
            ("Carrillos", item.carrillos),
            ("Labios", item.labios),
            ("Lengua", item.lengua),
            ("Piso de boca", item.piso_boca),
            ("Region retromolar", item.region_retromolar),
            ("Paladar duro/blando", item.paladar_duro_blando),
            ("Faringe", item.faringe),
            ("Encia libre/marginal", item.encia_libre_marginal),
        ]
        rows.extend(f"{label}: {value}" for label, value in soft_tissue_pairs if value)
        return [row for row in rows if row]

    def _anamnesis_rows(item: PeriodontalAnamnesis) -> list[str]:
        answer_labels = {"si": "Si", "no": "No", "no_recuerda": "No recuerda"}
        rows = [
            f"{question_labels.get(code, code)}: {answer_labels.get(answer, answer)}"
            for code, answer in item.answers.items()
        ]
        if item.salud_bucal_autopercibida:
            rows.append(f"Salud bucal autopercibida: {item.salud_bucal_autopercibida}")
        return rows

    def _radiographic_rows(item: RadiographicAnalysis) -> list[str]:
        rows = []
        for finding_type, detail in item.findings.items():
            if not isinstance(detail, dict):
                continue
            parts = [str(detail.get("organos_dentarios", ""))]
            if detail.get("porcentaje"):
                parts.append(f"{detail['porcentaje']}%")
            if detail.get("alteracion"):
                parts.append(str(detail["alteracion"]))
            rows.append(f"{finding_type}: " + " -- ".join(p for p in parts if p))
        if item.anexos_nota:
            rows.append(f"Anexos: {item.anexos_nota}")
        return rows

    def _odontogram_detail_rows(item: OdontogramDiagnosisDetail) -> list[str]:
        if item.edentulous_space_available is None:
            space_label = "-"
        elif item.edentulous_space_available:
            space_label = "Si"
        else:
            space_label = "No"
        rows = [
            f"Espacio interoclusal disponible: {space_label}",
            f"Kennedy superior: {item.kennedy_sup_class or '-'}"
            + (" (con modificacion)" if item.kennedy_sup_modification else ""),
            f"Kennedy inferior: {item.kennedy_inf_class or '-'}"
            + (" (con modificacion)" if item.kennedy_inf_modification else ""),
        ]
        for entry in item.fixed_prosthesis_analysis:
            if isinstance(entry, dict):
                rows.append(
                    f"Pieza {entry.get('tooth_fdi')}: relacion corona-raiz "
                    f"{entry.get('cr_relation')}"
                )
        return rows

    def _parallelometer_rows(item: ParallelometerAnalysis) -> list[str]:
        rows = []
        for entry in item.entries:
            if isinstance(entry, dict):
                rows.append(
                    f"Pieza {entry.get('organo_dental')}: {entry.get('caracteristicas')} -- "
                    f"plan: {entry.get('plan_tratamiento')}"
                )
        return rows

    def _rpd_rows(item: RemovablePartialDentureDesign) -> list[str]:
        pairs = [
            ("Conector mayor", item.conector_mayor),
            ("Conector menor", item.conector_menor),
            ("Retenedores directos", item.retenedores_directos),
            ("Conectores indirectos", item.conectores_indirectos),
            ("Base protesica", item.base_protesica),
            ("Dientes artificiales", item.dientes_artificiales),
        ]
        return [f"{label}: {value}" for label, value in pairs if value]

    def _tooth_diagnosis_rows(item: ToothDiagnosisEntry) -> list[str]:
        rows = [f"Pieza {tooth}: {text}" for tooth, text in item.diagnoses.items()]
        if item.observaciones:
            rows.append(f"Observaciones: {item.observaciones}")
        return rows

    def _tooth_treatment_plan_rows(item: ToothTreatmentPlanEntry) -> list[str]:
        rows = [f"Pieza {tooth}: {text}" for tooth, text in item.plans.items()]
        if item.observaciones:
            rows.append(f"Observaciones: {item.observaciones}")
        return rows

    data = OdontologicalHistoryPdfData(
        header=header,
        date_label=datetime.now(UTC).strftime("%d/%m/%Y"),
        patient_full_name=patient.full_name,
        patient_expediente_number=patient.expediente_number,
        odontogram_rows=[
            f"Pieza {tf.tooth_fdi}"
            + (f" ({tf.surface})" if tf.surface else "")
            + f": {odontogram_labels.get(tf.finding_code, tf.finding_code)}"
            for tf in odontogram_findings
        ],
        exam_rows=[row for item in exams for row in _exam_rows(item)],
        periodontal_anamnesis_rows=[row for item in anamneses for row in _anamnesis_rows(item)],
        radiographic_analysis_rows=[
            row for item in radiographic_analyses for row in _radiographic_rows(item)
        ],
        odontogram_diagnosis_detail_rows=[
            row for item in odontogram_details for row in _odontogram_detail_rows(item)
        ],
        parallelometer_analysis_rows=[
            row for item in parallelometer_analyses for row in _parallelometer_rows(item)
        ],
        removable_partial_denture_design_rows=[
            row for item in rpd_designs for row in _rpd_rows(item)
        ],
        tooth_diagnosis_rows=[
            row for item in tooth_diagnoses for row in _tooth_diagnosis_rows(item)
        ],
        tooth_treatment_plan_rows=[
            row for item in tooth_treatment_plans for row in _tooth_treatment_plan_rows(item)
        ],
    )

    pdf_bytes = build_odontological_history_pdf(data)

    await audit_service.log(
        db,
        action="odontological_history.pdf_read",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="patient",
        entity_id=str(patient_id),
    )
    await db.commit()
    return pdf_bytes
