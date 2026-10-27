import uuid
from collections.abc import Mapping
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import AppError
from app.core.storage import StorageBackend
from app.modules.documents.pdf_header import get_pdf_header_info
from app.modules.endodontic_history import rules
from app.modules.endodontic_history.models import (
    EndodonticDiagnosisTreatment,
    EndodonticInterrogation,
    EndodonticPeriodontalTest,
    EndodonticPulpSensitivityTest,
    EndodonticRadiographicInterpretation,
    EndodonticToothDiagnosisCode,
    EndodonticWorkingLength,
)
from app.modules.endodontic_history.pdf import (
    EndodonticHistoryPdfData,
    build_endodontic_history_pdf,
)
from app.modules.endodontic_history.schemas import (
    AnnulRequest,
    EndodonticDiagnosisTreatmentCreateRequest,
    EndodonticInterrogationCreateRequest,
    EndodonticPeriodontalTestCreateRequest,
    EndodonticPulpSensitivityTestCreateRequest,
    EndodonticRadiographicInterpretationCreateRequest,
    EndodonticToothDiagnosisCodeCreateRequest,
    EndodonticWorkingLengthCreateRequest,
)
from app.modules.patients.models import Patient

AnnullableEntry = (
    EndodonticInterrogation
    | EndodonticPulpSensitivityTest
    | EndodonticPeriodontalTest
    | EndodonticRadiographicInterpretation
    | EndodonticDiagnosisTreatment
    | EndodonticToothDiagnosisCode
    | EndodonticWorkingLength
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


def _check_fixed_keys(data: dict[str, bool], *, allowed: tuple[str, ...], field_name: str) -> None:
    """Valida un checklist cerrado (NO catalogo administrable, ver rules.py):
    las claves deben ser un subconjunto de `allowed`."""
    unknown = sorted(set(data.keys()) - set(allowed))
    if unknown:
        raise AppError(
            "INVALID_CHECKLIST_KEY",
            f"Clave(s) no reconocida(s) en '{field_name}': {', '.join(unknown)}",
            status_code=422,
        )


def _check_tooth_code(tooth_fdi: str | None) -> None:
    if tooth_fdi is not None and not rules.is_valid_permanent_tooth_code(tooth_fdi):
        raise AppError(
            "INVALID_TOOTH",
            f"Pieza FDI invalida (solo permanentes): {tooth_fdi}",
            status_code=422,
        )


def _check_canal_keys(canal_measurements: Mapping[str, object]) -> None:
    unknown = sorted(set(canal_measurements.keys()) - set(rules.CANAL_KEYS))
    if unknown:
        raise AppError(
            "INVALID_CHECKLIST_KEY",
            f"Clave(s) de conducto no reconocida(s): {', '.join(unknown)}",
            status_code=422,
        )


# --------------------------------------------------------------------------------
# 1. Interrogatorio + examen intrabucal/extrabucal.
# --------------------------------------------------------------------------------


async def list_interrogations(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[EndodonticInterrogation]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(EndodonticInterrogation)
        .where(
            EndodonticInterrogation.clinic_id == clinic_id,
            EndodonticInterrogation.patient_id == patient_id,
        )
        .order_by(EndodonticInterrogation.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_interrogation(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: EndodonticInterrogationCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> EndodonticInterrogation:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    _check_fixed_keys(data.antecedentes, allowed=rules.ANTECEDENTES_KEYS, field_name="antecedentes")
    _check_fixed_keys(data.dolor, allowed=rules.DOLOR_KEYS, field_name="dolor")
    _check_fixed_keys(data.estimulo, allowed=rules.ESTIMULO_KEYS, field_name="estimulo")
    _check_fixed_keys(
        data.examen_intrabucal,
        allowed=rules.EXAMEN_INTRABUCAL_KEYS,
        field_name="examen_intrabucal",
    )
    _check_fixed_keys(
        data.examen_extrabucal,
        allowed=rules.EXAMEN_EXTRABUCAL_KEYS,
        field_name="examen_extrabucal",
    )

    item = EndodonticInterrogation(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        antecedentes=data.antecedentes,
        antecedentes_otro_detalle=data.antecedentes_otro_detalle,
        dolor=data.dolor,
        dolor_otro_detalle=data.dolor_otro_detalle,
        estimulo=data.estimulo,
        estimulo_otro_detalle=data.estimulo_otro_detalle,
        examen_intrabucal=data.examen_intrabucal,
        examen_intrabucal_otro_detalle=data.examen_intrabucal_otro_detalle,
        examen_extrabucal=data.examen_extrabucal,
        examen_extrabucal_otro_detalle=data.examen_extrabucal_otro_detalle,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="endodontic_history.interrogation_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="endodontic_interrogation",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_interrogation(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> EndodonticInterrogation:
    item = await db.get(EndodonticInterrogation, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Interrogatorio de endodoncia no encontrado", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="endodontic_history.interrogation_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="endodontic_interrogation",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 2. Pruebas de sensibilidad pulpar.
# --------------------------------------------------------------------------------


async def list_pulp_sensitivity_tests(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[EndodonticPulpSensitivityTest]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(EndodonticPulpSensitivityTest)
        .where(
            EndodonticPulpSensitivityTest.clinic_id == clinic_id,
            EndodonticPulpSensitivityTest.patient_id == patient_id,
        )
        .order_by(EndodonticPulpSensitivityTest.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_pulp_sensitivity_test(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: EndodonticPulpSensitivityTestCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> EndodonticPulpSensitivityTest:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    item = EndodonticPulpSensitivityTest(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        frio=data.frio,
        calor=data.calor,
        fugaz=data.fugaz,
        persistente=data.persistente,
        localizado=data.localizado,
        irradiado=data.irradiado,
        decrece=data.decrece,
        incrementa=data.incrementa,
        diente_testigo_od=data.diente_testigo_od,
        prueba_cavidad=data.prueba_cavidad,
        prueba_electrica_od=data.prueba_electrica_od,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="endodontic_history.pulp_sensitivity_test_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="endodontic_pulp_sensitivity_test",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_pulp_sensitivity_test(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> EndodonticPulpSensitivityTest:
    item = await db.get(EndodonticPulpSensitivityTest, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Prueba de sensibilidad pulpar no encontrada", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="endodontic_history.pulp_sensitivity_test_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="endodontic_pulp_sensitivity_test",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 3. Pruebas periodontales.
# --------------------------------------------------------------------------------


async def list_periodontal_tests(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[EndodonticPeriodontalTest]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(EndodonticPeriodontalTest)
        .where(
            EndodonticPeriodontalTest.clinic_id == clinic_id,
            EndodonticPeriodontalTest.patient_id == patient_id,
        )
        .order_by(EndodonticPeriodontalTest.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_periodontal_test(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: EndodonticPeriodontalTestCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> EndodonticPeriodontalTest:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    _check_fixed_keys(
        data.percusion_horizontal, allowed=rules.PERCUSION_KEYS, field_name="percusion_horizontal"
    )
    _check_fixed_keys(
        data.percusion_vertical, allowed=rules.PERCUSION_KEYS, field_name="percusion_vertical"
    )
    if data.movilidad_horizontal_grado and data.movilidad_horizontal != "positiva":
        raise AppError(
            "INVALID_MOVILIDAD_GRADO",
            "El grado de movilidad horizontal solo aplica si movilidad_horizontal es 'positiva'",
            status_code=422,
        )
    if data.movilidad_vertical_grado and data.movilidad_vertical != "positiva":
        raise AppError(
            "INVALID_MOVILIDAD_GRADO",
            "El grado de movilidad vertical solo aplica si movilidad_vertical es 'positiva'",
            status_code=422,
        )

    item = EndodonticPeriodontalTest(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        percusion_horizontal=data.percusion_horizontal,
        movilidad_horizontal=data.movilidad_horizontal,
        movilidad_horizontal_grado=data.movilidad_horizontal_grado,
        percusion_vertical=data.percusion_vertical,
        movilidad_vertical=data.movilidad_vertical,
        movilidad_vertical_grado=data.movilidad_vertical_grado,
        palpacion=data.palpacion,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="endodontic_history.periodontal_test_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="endodontic_periodontal_test",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_periodontal_test(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> EndodonticPeriodontalTest:
    item = await db.get(EndodonticPeriodontalTest, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Prueba periodontal no encontrada", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="endodontic_history.periodontal_test_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="endodontic_periodontal_test",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 4. Interpretacion radiografica.
# --------------------------------------------------------------------------------


async def list_radiographic_interpretations(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[EndodonticRadiographicInterpretation]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(EndodonticRadiographicInterpretation)
        .where(
            EndodonticRadiographicInterpretation.clinic_id == clinic_id,
            EndodonticRadiographicInterpretation.patient_id == patient_id,
        )
        .order_by(EndodonticRadiographicInterpretation.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_radiographic_interpretation(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: EndodonticRadiographicInterpretationCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> EndodonticRadiographicInterpretation:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    _check_fixed_keys(data.camara, allowed=rules.CAMARA_KEYS, field_name="camara")
    _check_fixed_keys(data.conducto, allowed=rules.CONDUCTO_KEYS, field_name="conducto")
    _check_fixed_keys(data.periodonto, allowed=rules.PERIODONTO_KEYS, field_name="periodonto")

    item = EndodonticRadiographicInterpretation(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        camara=data.camara,
        camara_otro_detalle=data.camara_otro_detalle,
        conducto=data.conducto,
        conducto_otro_detalle=data.conducto_otro_detalle,
        periodonto=data.periodonto,
        periodonto_otro_detalle=data.periodonto_otro_detalle,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="endodontic_history.radiographic_interpretation_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="endodontic_radiographic_interpretation",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_radiographic_interpretation(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> EndodonticRadiographicInterpretation:
    item = await db.get(EndodonticRadiographicInterpretation, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Interpretacion radiografica no encontrada", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="endodontic_history.radiographic_interpretation_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="endodontic_radiographic_interpretation",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 5. Diagnostico y tratamiento.
# --------------------------------------------------------------------------------


async def list_diagnosis_treatments(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[EndodonticDiagnosisTreatment]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(EndodonticDiagnosisTreatment)
        .where(
            EndodonticDiagnosisTreatment.clinic_id == clinic_id,
            EndodonticDiagnosisTreatment.patient_id == patient_id,
        )
        .order_by(EndodonticDiagnosisTreatment.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_diagnosis_treatment(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: EndodonticDiagnosisTreatmentCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> EndodonticDiagnosisTreatment:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    _check_fixed_keys(data.tratamiento, allowed=rules.TRATAMIENTO_KEYS, field_name="tratamiento")
    _check_fixed_keys(data.cirugia, allowed=rules.CIRUGIA_KEYS, field_name="cirugia")

    item = EndodonticDiagnosisTreatment(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        diagnostico_pulpar=data.diagnostico_pulpar,
        diagnostico_periapical=data.diagnostico_periapical,
        tratamiento=data.tratamiento,
        cirugia=data.cirugia,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="endodontic_history.diagnosis_treatment_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="endodontic_diagnosis_treatment",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_diagnosis_treatment(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> EndodonticDiagnosisTreatment:
    item = await db.get(EndodonticDiagnosisTreatment, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Diagnostico y tratamiento no encontrado", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="endodontic_history.diagnosis_treatment_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="endodontic_diagnosis_treatment",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 6. Odontograma de diagnostico/evolucion -- 18 codigos por pieza.
# --------------------------------------------------------------------------------


async def list_tooth_diagnosis_codes(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    kind: str | None = None,
) -> list[EndodonticToothDiagnosisCode]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = select(EndodonticToothDiagnosisCode).where(
        EndodonticToothDiagnosisCode.clinic_id == clinic_id,
        EndodonticToothDiagnosisCode.patient_id == patient_id,
    )
    if kind is not None:
        stmt = stmt.where(EndodonticToothDiagnosisCode.kind == kind)
    stmt = stmt.order_by(EndodonticToothDiagnosisCode.created_at.desc())
    return list((await db.execute(stmt)).scalars().all())


async def create_tooth_diagnosis_code(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: EndodonticToothDiagnosisCodeCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> EndodonticToothDiagnosisCode:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    _check_tooth_code(data.tooth_fdi)
    if not rules.is_valid_endodontic_tooth_code(data.code):
        raise AppError(
            "INVALID_ENDODONTIC_TOOTH_CODE",
            f"Codigo de odontograma de endodoncia invalido: {data.code}",
            status_code=422,
        )

    # Decision documentada en models.py/PENDIENTES_CLINICOS.md (mismo patron
    # que PediatricToothAnnotation, Fase E): re-anotar la MISMA pieza con el
    # MISMO `kind` en el MISMO encounter anula automaticamente la anotacion
    # activa anterior de esa pieza+kind -- solo una vigente por pieza+kind.
    existing_stmt = select(EndodonticToothDiagnosisCode).where(
        EndodonticToothDiagnosisCode.clinic_id == clinic_id,
        EndodonticToothDiagnosisCode.patient_id == patient_id,
        EndodonticToothDiagnosisCode.encounter_id == data.encounter_id,
        EndodonticToothDiagnosisCode.tooth_fdi == data.tooth_fdi,
        EndodonticToothDiagnosisCode.kind == data.kind,
        EndodonticToothDiagnosisCode.is_active.is_(True),
    )
    for previous in (await db.execute(existing_stmt)).scalars().all():
        _annul(
            previous,
            AnnulRequest(
                reason="Reemplazada automaticamente por una nueva anotacion de la "
                "misma pieza y el mismo tipo (diagnostico/evolucion) en el mismo "
                "encuentro"
            ),
            actor_id,
        )

    item = EndodonticToothDiagnosisCode(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        tooth_fdi=data.tooth_fdi,
        kind=data.kind,
        code=data.code,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="endodontic_history.tooth_diagnosis_code_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="endodontic_tooth_diagnosis_code",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id), "tooth_fdi": data.tooth_fdi, "kind": data.kind},
    )
    await db.commit()
    return item


async def annul_tooth_diagnosis_code(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> EndodonticToothDiagnosisCode:
    item = await db.get(EndodonticToothDiagnosisCode, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError(
            "NOT_FOUND", "Anotacion de odontograma de endodoncia no encontrada", status_code=404
        )
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="endodontic_history.tooth_diagnosis_code_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="endodontic_tooth_diagnosis_code",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 7. Longitud de trabajo + datos de tratamiento.
# --------------------------------------------------------------------------------


async def list_working_lengths(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[EndodonticWorkingLength]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(EndodonticWorkingLength)
        .where(
            EndodonticWorkingLength.clinic_id == clinic_id,
            EndodonticWorkingLength.patient_id == patient_id,
        )
        .order_by(EndodonticWorkingLength.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_working_length(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: EndodonticWorkingLengthCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> EndodonticWorkingLength:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    _check_tooth_code(data.tooth_fdi)
    _check_canal_keys(data.canal_measurements)

    canal_measurements = {
        key: detail.model_dump() for key, detail in data.canal_measurements.items()
    }

    item = EndodonticWorkingLength(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        tooth_fdi=data.tooth_fdi,
        canal_measurements=canal_measurements,
        tecnica_instrumentacion=data.tecnica_instrumentacion,
        tecnica_obturacion=data.tecnica_obturacion,
        indicaciones=data.indicaciones,
        fecha_inicio=data.fecha_inicio,
        fecha_termino=data.fecha_termino,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="endodontic_history.working_length_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="endodontic_working_length",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_working_length(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> EndodonticWorkingLength:
    item = await db.get(EndodonticWorkingLength, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Longitud de trabajo no encontrada", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="endodontic_history.working_length_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="endodontic_working_length",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# PDF.
# --------------------------------------------------------------------------------


def _bool_label(value: bool | None) -> str:
    if value is None:
        return "-"
    return "Si" if value else "No"


def _checklist_labels(data: dict[str, bool]) -> list[str]:
    return [key for key, marked in data.items() if marked]


def _checklist_row(label: str, data: dict[str, bool], otro_detalle: str | None = None) -> str:
    marked = _checklist_labels(data)
    row = f"{label}: {', '.join(marked) if marked else 'sin hallazgos'}"
    if otro_detalle:
        row += f" ({otro_detalle})"
    return row


async def generate_endodontic_history_pdf(
    db: AsyncSession,
    storage: StorageBackend,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> bytes:
    """Historia Clinica de Endodoncia completa en PDF (Fase F): las 7
    secciones de esta fase. El odontograma de 18 codigos (diagnostico y
    evolucion) se lista como texto (pieza: codigo-nombre), igual criterio que
    `pediatric_history` para su odontograma pediatrico -- el dibujo visual
    completo queda para su propia vista en el frontend."""
    patient = await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    header = await get_pdf_header_info(db, storage, clinic_id=clinic_id)

    interrogations = [
        item
        for item in await list_interrogations(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    pulp_tests = [
        item
        for item in await list_pulp_sensitivity_tests(
            db, clinic_id=clinic_id, patient_id=patient_id
        )
        if item.is_active
    ]
    periodontal_tests = [
        item
        for item in await list_periodontal_tests(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    radiographic_interpretations = [
        item
        for item in await list_radiographic_interpretations(
            db, clinic_id=clinic_id, patient_id=patient_id
        )
        if item.is_active
    ]
    diagnosis_treatments = [
        item
        for item in await list_diagnosis_treatments(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    tooth_diagnosis_codes = [
        item
        for item in await list_tooth_diagnosis_codes(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    working_lengths = [
        item
        for item in await list_working_lengths(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]

    def _interrogation_rows(item: EndodonticInterrogation) -> list[str]:
        return [
            _checklist_row("Antecedentes", item.antecedentes, item.antecedentes_otro_detalle),
            _checklist_row("Dolor", item.dolor, item.dolor_otro_detalle),
            _checklist_row("Estimulo", item.estimulo, item.estimulo_otro_detalle),
            _checklist_row(
                "Examen intrabucal", item.examen_intrabucal, item.examen_intrabucal_otro_detalle
            ),
            _checklist_row(
                "Examen extrabucal", item.examen_extrabucal, item.examen_extrabucal_otro_detalle
            ),
        ]

    def _pulp_test_row(item: EndodonticPulpSensitivityTest) -> str:
        pairs = [
            ("frio", item.frio),
            ("calor", item.calor),
            ("fugaz", item.fugaz),
            ("persistente", item.persistente),
            ("localizado", item.localizado),
            ("irradiado", item.irradiado),
            ("decrece", item.decrece),
            ("incrementa", item.incrementa),
        ]
        marked = [label for label, value in pairs if value]
        row = f"Prueba: {', '.join(marked) if marked else 'sin hallazgos'}"
        extras = []
        if item.diente_testigo_od:
            extras.append(f"diente testigo O.D. {item.diente_testigo_od}")
        if item.prueba_cavidad:
            extras.append(f"prueba de cavidad {item.prueba_cavidad}")
        if item.prueba_electrica_od:
            extras.append(f"prueba electrica O.D. {item.prueba_electrica_od}")
        if extras:
            row += f" ({'; '.join(extras)})"
        return row

    def _periodontal_test_rows(item: EndodonticPeriodontalTest) -> list[str]:
        rows = [
            _checklist_row("Percusion horizontal", item.percusion_horizontal),
            _checklist_row("Percusion vertical", item.percusion_vertical),
        ]
        if item.movilidad_horizontal:
            row = f"Movilidad horizontal: {item.movilidad_horizontal}"
            if item.movilidad_horizontal_grado:
                row += f" (grado {item.movilidad_horizontal_grado})"
            rows.append(row)
        if item.movilidad_vertical:
            row = f"Movilidad vertical: {item.movilidad_vertical}"
            if item.movilidad_vertical_grado:
                row += f" (grado {item.movilidad_vertical_grado})"
            rows.append(row)
        if item.palpacion:
            rows.append(f"Palpacion: {item.palpacion}")
        return rows

    def _radiographic_interpretation_rows(
        item: EndodonticRadiographicInterpretation,
    ) -> list[str]:
        return [
            _checklist_row("Camara", item.camara, item.camara_otro_detalle),
            _checklist_row("Conducto", item.conducto, item.conducto_otro_detalle),
            _checklist_row("Periodonto", item.periodonto, item.periodonto_otro_detalle),
        ]

    def _diagnosis_treatment_rows(item: EndodonticDiagnosisTreatment) -> list[str]:
        rows = []
        if item.diagnostico_pulpar:
            rows.append(f"Diagnostico pulpar: {item.diagnostico_pulpar}")
        if item.diagnostico_periapical:
            rows.append(f"Diagnostico periapical: {item.diagnostico_periapical}")
        rows.append(_checklist_row("Tratamiento", item.tratamiento))
        rows.append(_checklist_row("Cirugia", item.cirugia))
        return rows

    def _tooth_diagnosis_code_row(item: EndodonticToothDiagnosisCode) -> str:
        label = rules.ENDODONTIC_TOOTH_CODE_LABELS.get(item.code, str(item.code))
        return f"Pieza {item.tooth_fdi} ({item.kind}): {item.code} - {label}"

    def _working_length_rows(item: EndodonticWorkingLength) -> list[str]:
        rows = []
        if item.tooth_fdi:
            rows.append(f"Pieza: {item.tooth_fdi}")
        for canal_key, detail in item.canal_measurements.items():
            parts = [
                f"aparente RX: {detail.get('aparente_rx')}" if detail.get("aparente_rx") else None,
                (
                    f"real/localizador: {detail.get('real_localizador')}"
                    if detail.get("real_localizador")
                    else None
                ),
                f"relacion: {detail.get('relacion')}" if detail.get("relacion") else None,
            ]
            detail_text = "; ".join(p for p in parts if p)
            rows.append(f"Conducto {canal_key}: {detail_text if detail_text else 'sin datos'}")
        if item.tecnica_instrumentacion:
            rows.append(f"Tecnica de instrumentacion: {item.tecnica_instrumentacion}")
        if item.tecnica_obturacion:
            rows.append(f"Tecnica de obturacion: {item.tecnica_obturacion}")
        if item.indicaciones:
            rows.append(f"Indicaciones: {item.indicaciones}")
        if item.fecha_inicio:
            rows.append(f"Fecha de inicio: {item.fecha_inicio}")
        if item.fecha_termino:
            rows.append(f"Fecha de termino: {item.fecha_termino}")
        return rows

    data = EndodonticHistoryPdfData(
        header=header,
        date_label=datetime.now(UTC).strftime("%d/%m/%Y"),
        patient_full_name=patient.full_name,
        patient_expediente_number=patient.expediente_number,
        interrogation_rows=[row for item in interrogations for row in _interrogation_rows(item)],
        pulp_sensitivity_test_rows=[_pulp_test_row(item) for item in pulp_tests],
        periodontal_test_rows=[
            row for item in periodontal_tests for row in _periodontal_test_rows(item)
        ],
        radiographic_interpretation_rows=[
            row
            for item in radiographic_interpretations
            for row in _radiographic_interpretation_rows(item)
        ],
        diagnosis_treatment_rows=[
            row for item in diagnosis_treatments for row in _diagnosis_treatment_rows(item)
        ],
        tooth_diagnosis_code_rows=[
            _tooth_diagnosis_code_row(item) for item in tooth_diagnosis_codes
        ],
        working_length_rows=[row for item in working_lengths for row in _working_length_rows(item)],
    )

    pdf_bytes = build_endodontic_history_pdf(data)

    await audit_service.log(
        db,
        action="endodontic_history.pdf_read",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="patient",
        entity_id=str(patient_id),
    )
    await db.commit()
    return pdf_bytes
