import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import AppError
from app.core.storage import StorageBackend
from app.modules.catalogs import service as catalogs_service
from app.modules.documents.pdf_header import get_pdf_header_info
from app.modules.patients.models import Patient
from app.modules.pediatric_history import rules
from app.modules.pediatric_history.models import (
    PediatricBehaviorMaturity,
    PediatricEruptionDentition,
    PediatricOcclusion,
    PediatricOralHabits,
    PediatricPerinatalHistory,
    PediatricToothAnnotation,
)
from app.modules.pediatric_history.pdf import (
    PediatricHistoryPdfData,
    build_pediatric_history_pdf,
)
from app.modules.pediatric_history.schemas import (
    AnnulRequest,
    PediatricBehaviorMaturityCreateRequest,
    PediatricEruptionDentitionCreateRequest,
    PediatricOcclusionCreateRequest,
    PediatricOralHabitsCreateRequest,
    PediatricPerinatalHistoryCreateRequest,
    PediatricToothAnnotationCreateRequest,
)

AnnullableEntry = (
    PediatricPerinatalHistory
    | PediatricOralHabits
    | PediatricBehaviorMaturity
    | PediatricOcclusion
    | PediatricEruptionDentition
    | PediatricToothAnnotation
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


async def _catalog_label_map(
    db: AsyncSession, *, clinic_id: uuid.UUID, catalog_type: str
) -> dict[str, str]:
    items = await catalogs_service.list_items(
        db, clinic_id=clinic_id, catalog_type=catalog_type, include_inactive=True
    )
    return {item.code: item.name for item in items}


# --------------------------------------------------------------------------------
# 1. Antecedentes perinatales y primer ano de vida.
# --------------------------------------------------------------------------------


async def list_perinatal_histories(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[PediatricPerinatalHistory]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(PediatricPerinatalHistory)
        .where(
            PediatricPerinatalHistory.clinic_id == clinic_id,
            PediatricPerinatalHistory.patient_id == patient_id,
        )
        .order_by(PediatricPerinatalHistory.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_perinatal_history(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: PediatricPerinatalHistoryCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> PediatricPerinatalHistory:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    item = PediatricPerinatalHistory(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        problemas_embarazo_perinatales=data.problemas_embarazo_perinatales,
        tomo_medicamentos_embarazo=data.tomo_medicamentos_embarazo,
        tomo_medicamentos_embarazo_cuales=data.tomo_medicamentos_embarazo_cuales,
        embarazo_observaciones=data.embarazo_observaciones,
        tomo_medicamentos_primer_ano=data.tomo_medicamentos_primer_ano,
        tomo_medicamentos_primer_ano_cuales=data.tomo_medicamentos_primer_ano_cuales,
        vacunas_completas=data.vacunas_completas,
        fecha_ultima_visita_dentista=data.fecha_ultima_visita_dentista,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="pediatric_history.perinatal_history_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="pediatric_perinatal_history",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_perinatal_history(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> PediatricPerinatalHistory:
    item = await db.get(PediatricPerinatalHistory, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError(
            "NOT_FOUND", "Antecedente perinatal/primer ano no encontrado", status_code=404
        )
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="pediatric_history.perinatal_history_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="pediatric_perinatal_history",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 2. Habitos y antecedentes bucales.
# --------------------------------------------------------------------------------


async def list_oral_habits(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[PediatricOralHabits]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(PediatricOralHabits)
        .where(
            PediatricOralHabits.clinic_id == clinic_id,
            PediatricOralHabits.patient_id == patient_id,
        )
        .order_by(PediatricOralHabits.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_oral_habits(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: PediatricOralHabitsCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> PediatricOralHabits:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    item = PediatricOralHabits(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        cepilla_despues_alimento=data.cepilla_despues_alimento,
        sangran_encias_sin_cepillar=data.sangran_encias_sin_cepillar,
        sabe_que_es_fluor=data.sabe_que_es_fluor,
        fluoruro_sistematico_aplicado=data.fluoruro_sistematico_aplicado,
        diente_extraido=data.diente_extraido,
        accidentes_fracturas_dentales=data.accidentes_fracturas_dentales,
        dolor_dental_reciente=data.dolor_dental_reciente,
        bruxismo_nocturno=data.bruxismo_nocturno,
        respira_boca_frecuente=data.respira_boca_frecuente,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="pediatric_history.oral_habits_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="pediatric_oral_habits",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_oral_habits(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> PediatricOralHabits:
    item = await db.get(PediatricOralHabits, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Habitos bucales no encontrados", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="pediatric_history.oral_habits_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="pediatric_oral_habits",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 3. Madurez y conducta.
# --------------------------------------------------------------------------------


async def list_behavior_maturities(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[PediatricBehaviorMaturity]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(PediatricBehaviorMaturity)
        .where(
            PediatricBehaviorMaturity.clinic_id == clinic_id,
            PediatricBehaviorMaturity.patient_id == patient_id,
        )
        .order_by(PediatricBehaviorMaturity.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_behavior_maturity(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: PediatricBehaviorMaturityCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> PediatricBehaviorMaturity:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    await _check_codes_against_catalog(
        db,
        clinic_id=clinic_id,
        catalog_type="pediatric_character",
        codes=[data.caracter] if data.caracter else [],
        error_code="INVALID_PEDIATRIC_CHARACTER",
    )

    item = PediatricBehaviorMaturity(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        experiencia_desfavorable_dentista=data.experiencia_desfavorable_dentista,
        se_relaciona_medico=data.se_relaciona_medico,
        controla_esfinteres=data.controla_esfinteres,
        toma_biberon_actualmente=data.toma_biberon_actualmente,
        edad_dejo_biberon=data.edad_dejo_biberon,
        succion_labio_dedo=data.succion_labio_dedo,
        muerde_objetos_unas=data.muerde_objetos_unas,
        relacion_otros_ninos=data.relacion_otros_ninos,
        caracter=data.caracter,
        observaciones=data.observaciones,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="pediatric_history.behavior_maturity_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="pediatric_behavior_maturity",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_behavior_maturity(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> PediatricBehaviorMaturity:
    item = await db.get(PediatricBehaviorMaturity, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Madurez y conducta no encontrada", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="pediatric_history.behavior_maturity_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="pediatric_behavior_maturity",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 4. Oclusion y alineamiento.
# --------------------------------------------------------------------------------


async def list_occlusions(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[PediatricOcclusion]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(PediatricOcclusion)
        .where(
            PediatricOcclusion.clinic_id == clinic_id,
            PediatricOcclusion.patient_id == patient_id,
        )
        .order_by(PediatricOcclusion.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_occlusion(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: PediatricOcclusionCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> PediatricOcclusion:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    await _check_codes_against_catalog(
        db,
        clinic_id=clinic_id,
        catalog_type="terminal_plane",
        codes=[c for c in (data.planos_terminales_izq, data.planos_terminales_der) if c],
        error_code="INVALID_TERMINAL_PLANE",
    )

    item = PediatricOcclusion(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        planos_terminales_izq=data.planos_terminales_izq,
        planos_terminales_der=data.planos_terminales_der,
        angle_molar_izq=data.angle_molar_izq,
        angle_molar_der=data.angle_molar_der,
        overjet_mm=data.overjet_mm,
        overbite_mm=data.overbite_mm,
        mordida_cruzada=data.mordida_cruzada,
        diastema=data.diastema,
        mordida_abierta_ante_mm=data.mordida_abierta_ante_mm,
        mordida_abierta_post_mm=data.mordida_abierta_post_mm,
        linea_media=data.linea_media,
        clasificacion_angle=data.clasificacion_angle,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="pediatric_history.occlusion_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="pediatric_occlusion",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_occlusion(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> PediatricOcclusion:
    item = await db.get(PediatricOcclusion, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Oclusion y alineamiento no encontrada", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="pediatric_history.occlusion_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="pediatric_occlusion",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 5. Erupcion y denticion.
# --------------------------------------------------------------------------------


async def list_eruption_dentitions(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[PediatricEruptionDentition]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(PediatricEruptionDentition)
        .where(
            PediatricEruptionDentition.clinic_id == clinic_id,
            PediatricEruptionDentition.patient_id == patient_id,
        )
        .order_by(PediatricEruptionDentition.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_eruption_dentition(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: PediatricEruptionDentitionCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> PediatricEruptionDentition:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    item = PediatricEruptionDentition(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        secuencia_normal=data.secuencia_normal,
        perdida_prematura=data.perdida_prematura,
        retencion_prolongada=data.retencion_prolongada,
        erupcion_retardada=data.erupcion_retardada,
        falta_contacto_proximal=data.falta_contacto_proximal,
        malposicion_dentaria=data.malposicion_dentaria,
        otras_anormalidades=data.otras_anormalidades,
        edad_dental=data.edad_dental,
        estado_general_higiene=data.estado_general_higiene,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="pediatric_history.eruption_dentition_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="pediatric_eruption_dentition",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_eruption_dentition(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> PediatricEruptionDentition:
    item = await db.get(PediatricEruptionDentition, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Erupcion y denticion no encontrada", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="pediatric_history.eruption_dentition_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="pediatric_eruption_dentition",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 6. Odontograma pediatrico -- anotaciones por pieza.
# --------------------------------------------------------------------------------


async def list_tooth_annotations(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[PediatricToothAnnotation]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(PediatricToothAnnotation)
        .where(
            PediatricToothAnnotation.clinic_id == clinic_id,
            PediatricToothAnnotation.patient_id == patient_id,
        )
        .order_by(PediatricToothAnnotation.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_tooth_annotation(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: PediatricToothAnnotationCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> PediatricToothAnnotation:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    if not rules.is_valid_tooth_code(data.tooth_fdi):
        raise AppError(
            "INVALID_TOOTH",
            f"Pieza FDI invalida: {data.tooth_fdi}",
            status_code=422,
        )
    await _check_codes_against_catalog(
        db,
        clinic_id=clinic_id,
        catalog_type="pediatric_tooth_anomaly",
        codes=[data.anomaly_code],
        error_code="INVALID_PEDIATRIC_TOOTH_ANOMALY",
    )

    # Decision documentada en models.py/PENDIENTES_CLINICOS.md: re-anotar la
    # MISMA pieza en el MISMO encounter anula automaticamente la anotacion
    # activa anterior para esa pieza (solo una vigente), en vez de permitir
    # varias activas simultaneas.
    existing_stmt = select(PediatricToothAnnotation).where(
        PediatricToothAnnotation.clinic_id == clinic_id,
        PediatricToothAnnotation.patient_id == patient_id,
        PediatricToothAnnotation.encounter_id == data.encounter_id,
        PediatricToothAnnotation.tooth_fdi == data.tooth_fdi,
        PediatricToothAnnotation.is_active.is_(True),
    )
    for previous in (await db.execute(existing_stmt)).scalars().all():
        _annul(
            previous,
            AnnulRequest(
                reason="Reemplazada automaticamente por una nueva anotacion de la "
                "misma pieza en el mismo encuentro"
            ),
            actor_id,
        )

    item = PediatricToothAnnotation(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        tooth_fdi=data.tooth_fdi,
        anomaly_code=data.anomaly_code,
        hipoplasia_detail=data.hipoplasia_detail,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="pediatric_history.tooth_annotation_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="pediatric_tooth_annotation",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id), "tooth_fdi": data.tooth_fdi},
    )
    await db.commit()
    return item


async def annul_tooth_annotation(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> PediatricToothAnnotation:
    item = await db.get(PediatricToothAnnotation, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Anotacion de pieza no encontrada", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="pediatric_history.tooth_annotation_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="pediatric_tooth_annotation",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# PDF.
# --------------------------------------------------------------------------------


async def generate_pediatric_history_pdf(
    db: AsyncSession,
    storage: StorageBackend,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> bytes:
    """Historia Clinica Pediatrica completa en PDF (Fase E): las 6 secciones de
    esta fase. NO incluye el dibujo del odontograma pediatrico ni el plan de
    tratamiento permanente/temporal por pieza (se consultan en sus propias
    vistas: el odontograma visual es complejo de reutilizar en este PDF de
    texto/xhtml2pdf, y el plan ya tiene su propio PDF en
    `odontological_history` -- decision documentada en
    docs/PENDIENTES_CLINICOS.md). Se listan las anotaciones de anomalia por
    pieza como texto, que si cabe bien en este formato."""
    patient = await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    header = await get_pdf_header_info(db, storage, clinic_id=clinic_id)

    character_labels = await _catalog_label_map(
        db, clinic_id=clinic_id, catalog_type="pediatric_character"
    )
    terminal_plane_labels = await _catalog_label_map(
        db, clinic_id=clinic_id, catalog_type="terminal_plane"
    )
    anomaly_labels = await _catalog_label_map(
        db, clinic_id=clinic_id, catalog_type="pediatric_tooth_anomaly"
    )

    perinatal_histories = [
        item
        for item in await list_perinatal_histories(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    oral_habits_list = [
        item
        for item in await list_oral_habits(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    behavior_maturities = [
        item
        for item in await list_behavior_maturities(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    occlusions = [
        item
        for item in await list_occlusions(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    eruption_dentitions = [
        item
        for item in await list_eruption_dentitions(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    tooth_annotations = [
        item
        for item in await list_tooth_annotations(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]

    def _bool_label(value: bool | None) -> str:
        if value is None:
            return "-"
        return "Si" if value else "No"

    def _perinatal_rows(item: PediatricPerinatalHistory) -> list[str]:
        rows = [
            (
                f"Problemas en el embarazo/periodo perinatal: "
                f"{item.problemas_embarazo_perinatales}"
                if item.problemas_embarazo_perinatales
                else None
            ),
            f"Tomo medicamentos durante el embarazo: "
            f"{_bool_label(item.tomo_medicamentos_embarazo)}"
            + (
                f" ({item.tomo_medicamentos_embarazo_cuales})"
                if item.tomo_medicamentos_embarazo_cuales
                else ""
            ),
            (
                f"Observaciones del embarazo: {item.embarazo_observaciones}"
                if item.embarazo_observaciones
                else None
            ),
            f"Tomo medicamentos en el primer ano de vida: "
            f"{_bool_label(item.tomo_medicamentos_primer_ano)}"
            + (
                f" ({item.tomo_medicamentos_primer_ano_cuales})"
                if item.tomo_medicamentos_primer_ano_cuales
                else ""
            ),
            f"Vacunas completas: {_bool_label(item.vacunas_completas)}",
            (
                f"Fecha de la ultima visita al dentista: {item.fecha_ultima_visita_dentista}"
                if item.fecha_ultima_visita_dentista
                else None
            ),
        ]
        return [row for row in rows if row]

    def _oral_habits_rows(item: PediatricOralHabits) -> list[str]:
        pairs = [
            ("Se cepilla despues de cada alimento", item.cepilla_despues_alimento),
            ("Le sangran las encias al cepillarse", item.sangran_encias_sin_cepillar),
            ("Sabe que es el fluor", item.sabe_que_es_fluor),
            ("Se le ha aplicado fluoruro sistematico", item.fluoruro_sistematico_aplicado),
            ("Se le ha extraido algun diente", item.diente_extraido),
            ("Ha tenido accidentes/fracturas dentales", item.accidentes_fracturas_dentales),
            ("Dolor dental reciente", item.dolor_dental_reciente),
            ("Bruxismo nocturno", item.bruxismo_nocturno),
            ("Respira por la boca frecuentemente", item.respira_boca_frecuente),
        ]
        return [f"{label}: {_bool_label(value)}" for label, value in pairs]

    def _behavior_rows(item: PediatricBehaviorMaturity) -> list[str]:
        pairs = [
            ("Experiencia desfavorable con el dentista", item.experiencia_desfavorable_dentista),
            ("Se relaciona bien con el medico", item.se_relaciona_medico),
            ("Controla esfinteres", item.controla_esfinteres),
            ("Toma biberon actualmente", item.toma_biberon_actualmente),
            ("Succion de labio/dedo", item.succion_labio_dedo),
            ("Muerde objetos/unas", item.muerde_objetos_unas),
        ]
        rows = [f"{label}: {_bool_label(value)}" for label, value in pairs]
        if item.edad_dejo_biberon:
            rows.append(f"Edad en que dejo el biberon: {item.edad_dejo_biberon}")
        if item.relacion_otros_ninos:
            rows.append(f"Relacion con otros ninos: {item.relacion_otros_ninos}")
        if item.caracter:
            rows.append(f"Caracter: {character_labels.get(item.caracter, item.caracter)}")
        if item.observaciones:
            rows.append(f"Observaciones: {item.observaciones}")
        return rows

    def _occlusion_rows(item: PediatricOcclusion) -> list[str]:
        rows = []
        if item.planos_terminales_izq:
            rows.append(
                "Planos terminales izquierdo: "
                + terminal_plane_labels.get(item.planos_terminales_izq, item.planos_terminales_izq)
            )
        if item.planos_terminales_der:
            rows.append(
                "Planos terminales derecho: "
                + terminal_plane_labels.get(item.planos_terminales_der, item.planos_terminales_der)
            )
        if item.angle_molar_izq:
            rows.append(f"Relacion molar de Angle izquierda: {item.angle_molar_izq}")
        if item.angle_molar_der:
            rows.append(f"Relacion molar de Angle derecha: {item.angle_molar_der}")
        if item.overjet_mm is not None:
            rows.append(f"Overjet: {item.overjet_mm} mm")
        if item.overbite_mm is not None:
            rows.append(f"Overbite: {item.overbite_mm} mm")
        rows.append(f"Mordida cruzada: {_bool_label(item.mordida_cruzada)}")
        rows.append(f"Diastema: {_bool_label(item.diastema)}")
        if item.mordida_abierta_ante_mm is not None:
            rows.append(f"Mordida abierta anterior: {item.mordida_abierta_ante_mm} mm")
        if item.mordida_abierta_post_mm is not None:
            rows.append(f"Mordida abierta posterior: {item.mordida_abierta_post_mm} mm")
        if item.linea_media:
            rows.append(f"Linea media: {item.linea_media}")
        if item.clasificacion_angle:
            rows.append(f"Clasificacion de Angle: {item.clasificacion_angle}")
        return rows

    def _eruption_rows(item: PediatricEruptionDentition) -> list[str]:
        pairs = [
            ("Secuencia normal de erupcion", item.secuencia_normal),
            ("Perdida prematura", item.perdida_prematura),
            ("Retencion prolongada", item.retencion_prolongada),
            ("Erupcion retardada", item.erupcion_retardada),
            ("Falta de contacto proximal", item.falta_contacto_proximal),
            ("Malposicion dentaria", item.malposicion_dentaria),
        ]
        rows = [f"{label}: {_bool_label(value)}" for label, value in pairs]
        if item.otras_anormalidades:
            rows.append(f"Otras anormalidades: {item.otras_anormalidades}")
        if item.edad_dental:
            rows.append(f"Edad dental: {item.edad_dental}")
        if item.estado_general_higiene:
            rows.append(f"Estado general de higiene: {item.estado_general_higiene}")
        return rows

    def _tooth_annotation_row(item: PediatricToothAnnotation) -> str:
        label = anomaly_labels.get(item.anomaly_code, item.anomaly_code)
        row = f"Pieza {item.tooth_fdi}: {label}"
        if item.hipoplasia_detail:
            row += f" ({item.hipoplasia_detail})"
        return row

    data = PediatricHistoryPdfData(
        header=header,
        date_label=datetime.now(UTC).strftime("%d/%m/%Y"),
        patient_full_name=patient.full_name,
        patient_expediente_number=patient.expediente_number,
        perinatal_rows=[row for item in perinatal_histories for row in _perinatal_rows(item)],
        oral_habits_rows=[row for item in oral_habits_list for row in _oral_habits_rows(item)],
        behavior_maturity_rows=[
            row for item in behavior_maturities for row in _behavior_rows(item)
        ],
        occlusion_rows=[row for item in occlusions for row in _occlusion_rows(item)],
        eruption_dentition_rows=[
            row for item in eruption_dentitions for row in _eruption_rows(item)
        ],
        tooth_annotation_rows=[_tooth_annotation_row(item) for item in tooth_annotations],
    )

    pdf_bytes = build_pediatric_history_pdf(data)

    await audit_service.log(
        db,
        action="pediatric_history.pdf_read",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="patient",
        entity_id=str(patient_id),
    )
    await db.commit()
    return pdf_bytes
