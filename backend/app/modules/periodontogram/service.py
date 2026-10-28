import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import AppError
from app.core.storage import StorageBackend
from app.modules.documents.pdf_header import get_pdf_header_info
from app.modules.patients.models import Patient
from app.modules.periodontogram import rules
from app.modules.periodontogram.models import (
    OcclusalContactEntry,
    PeriodontalIndexEntry,
    PeriodontalProbingSite,
    PeriodontalToothMeasurement,
    PeriodontogramObservation,
)
from app.modules.periodontogram.pdf import (
    PeriodontogramPdfData,
    build_periodontogram_pdf,
)
from app.modules.periodontogram.schemas import (
    AnnulRequest,
    GingivalIndexSummary,
    IndicesSummaryOut,
    OcclusalContactEntryCreateRequest,
    PeriodontalIndexEntryCreateRequest,
    PeriodontalProbingSiteCreateRequest,
    PeriodontalToothMeasurementCreateRequest,
    PeriodontogramObservationCreateRequest,
    PlaqueIndexSummary,
)

AnnullableEntry = (
    PeriodontalProbingSite
    | PeriodontalToothMeasurement
    | PeriodontalIndexEntry
    | OcclusalContactEntry
    | PeriodontogramObservation
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


def _check_tooth_code(tooth_fdi: str) -> None:
    if not rules.is_valid_permanent_tooth_code(tooth_fdi):
        raise AppError(
            "INVALID_TOOTH",
            f"Pieza FDI invalida (solo permanentes): {tooth_fdi}",
            status_code=422,
        )


# --------------------------------------------------------------------------------
# 1. Sondeo periodontal -- 6 sitios por pieza.
# --------------------------------------------------------------------------------


async def list_probing_sites(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[PeriodontalProbingSite]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(PeriodontalProbingSite)
        .where(
            PeriodontalProbingSite.clinic_id == clinic_id,
            PeriodontalProbingSite.patient_id == patient_id,
        )
        .order_by(PeriodontalProbingSite.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_probing_site(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: PeriodontalProbingSiteCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> PeriodontalProbingSite:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    _check_tooth_code(data.tooth_fdi)

    # Decision documentada en models.py/PENDIENTES_CLINICOS.md (mismo patron
    # que PediatricToothAnnotation/EndodonticToothDiagnosisCode): re-anotar
    # la MISMA pieza+sitio en el MISMO encounter anula automaticamente la
    # anotacion activa anterior de esa pieza+sitio.
    existing_stmt = select(PeriodontalProbingSite).where(
        PeriodontalProbingSite.clinic_id == clinic_id,
        PeriodontalProbingSite.patient_id == patient_id,
        PeriodontalProbingSite.encounter_id == data.encounter_id,
        PeriodontalProbingSite.tooth_fdi == data.tooth_fdi,
        PeriodontalProbingSite.site == data.site,
        PeriodontalProbingSite.is_active.is_(True),
    )
    for previous in (await db.execute(existing_stmt)).scalars().all():
        _annul(
            previous,
            AnnulRequest(
                reason="Reemplazada automaticamente por un nuevo sondeo de la "
                "misma pieza y el mismo sitio en el mismo encuentro"
            ),
            actor_id,
        )

    item = PeriodontalProbingSite(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        tooth_fdi=data.tooth_fdi,
        site=data.site,
        probing_depth_mm=data.probing_depth_mm,
        recession_mm=data.recession_mm,
        bleeding_on_probing=data.bleeding_on_probing,
        suppuration=data.suppuration,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="periodontogram.probing_site_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="periodontal_probing_site",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id), "tooth_fdi": data.tooth_fdi, "site": data.site},
    )
    await db.commit()
    return item


async def annul_probing_site(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> PeriodontalProbingSite:
    item = await db.get(PeriodontalProbingSite, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Sitio de sondeo periodontal no encontrado", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="periodontogram.probing_site_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="periodontal_probing_site",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 2. Medicion por pieza -- movilidad y furcacion.
# --------------------------------------------------------------------------------


async def list_tooth_measurements(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[PeriodontalToothMeasurement]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(PeriodontalToothMeasurement)
        .where(
            PeriodontalToothMeasurement.clinic_id == clinic_id,
            PeriodontalToothMeasurement.patient_id == patient_id,
        )
        .order_by(PeriodontalToothMeasurement.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_tooth_measurement(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: PeriodontalToothMeasurementCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> PeriodontalToothMeasurement:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    _check_tooth_code(data.tooth_fdi)

    # Decision documentada en models.py (mismo patron que la seccion 1): re-
    # anotar la MISMA pieza en el MISMO encounter anula automaticamente la
    # medicion activa anterior de esa pieza.
    existing_stmt = select(PeriodontalToothMeasurement).where(
        PeriodontalToothMeasurement.clinic_id == clinic_id,
        PeriodontalToothMeasurement.patient_id == patient_id,
        PeriodontalToothMeasurement.encounter_id == data.encounter_id,
        PeriodontalToothMeasurement.tooth_fdi == data.tooth_fdi,
        PeriodontalToothMeasurement.is_active.is_(True),
    )
    for previous in (await db.execute(existing_stmt)).scalars().all():
        _annul(
            previous,
            AnnulRequest(
                reason="Reemplazada automaticamente por una nueva medicion de la "
                "misma pieza en el mismo encuentro"
            ),
            actor_id,
        )

    item = PeriodontalToothMeasurement(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        tooth_fdi=data.tooth_fdi,
        mobility_grade=data.mobility_grade,
        furcation_grade=data.furcation_grade,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="periodontogram.tooth_measurement_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="periodontal_tooth_measurement",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id), "tooth_fdi": data.tooth_fdi},
    )
    await db.commit()
    return item


async def annul_tooth_measurement(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> PeriodontalToothMeasurement:
    item = await db.get(PeriodontalToothMeasurement, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Medicion por pieza no encontrada", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="periodontogram.tooth_measurement_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="periodontal_tooth_measurement",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 3. Indices de placa dentobacteriana y gingival.
# --------------------------------------------------------------------------------


async def list_index_entries(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    index_type: str | None = None,
) -> list[PeriodontalIndexEntry]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = select(PeriodontalIndexEntry).where(
        PeriodontalIndexEntry.clinic_id == clinic_id,
        PeriodontalIndexEntry.patient_id == patient_id,
    )
    if index_type is not None:
        stmt = stmt.where(PeriodontalIndexEntry.index_type == index_type)
    stmt = stmt.order_by(PeriodontalIndexEntry.created_at.desc())
    return list((await db.execute(stmt)).scalars().all())


async def create_index_entry(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: PeriodontalIndexEntryCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> PeriodontalIndexEntry:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    _check_tooth_code(data.tooth_fdi)

    # Decision documentada en models.py: re-anotar la MISMA
    # pieza+index_type+surface en el MISMO encounter anula automaticamente la
    # anterior.
    existing_stmt = select(PeriodontalIndexEntry).where(
        PeriodontalIndexEntry.clinic_id == clinic_id,
        PeriodontalIndexEntry.patient_id == patient_id,
        PeriodontalIndexEntry.encounter_id == data.encounter_id,
        PeriodontalIndexEntry.tooth_fdi == data.tooth_fdi,
        PeriodontalIndexEntry.index_type == data.index_type,
        PeriodontalIndexEntry.surface == data.surface,
        PeriodontalIndexEntry.is_active.is_(True),
    )
    for previous in (await db.execute(existing_stmt)).scalars().all():
        _annul(
            previous,
            AnnulRequest(
                reason="Reemplazada automaticamente por una nueva captura de la "
                "misma pieza, el mismo tipo de indice y la misma superficie en "
                "el mismo encuentro"
            ),
            actor_id,
        )

    item = PeriodontalIndexEntry(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        tooth_fdi=data.tooth_fdi,
        index_type=data.index_type,
        surface=data.surface,
        grade=data.grade,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="periodontogram.index_entry_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="periodontal_index_entry",
        entity_id=str(item.id),
        details={
            "patient_id": str(patient_id),
            "tooth_fdi": data.tooth_fdi,
            "index_type": data.index_type,
            "surface": data.surface,
        },
    )
    await db.commit()
    return item


async def annul_index_entry(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> PeriodontalIndexEntry:
    item = await db.get(PeriodontalIndexEntry, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Entrada de indice periodontal no encontrada", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="periodontogram.index_entry_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="periodontal_index_entry",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


async def get_indices_summary(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    encounter_id: uuid.UUID | None = None,
) -> IndicesSummaryOut:
    """Indices de placa dentobacteriana/gingival calculados al vuelo (nunca
    persistidos, ver rules.py) para un encounter: el especificado via query
    param, o -- si no se especifica -- el encounter mas reciente con al
    menos una entrada activa de `PeriodontalIndexEntry` (decision de diseno:
    "mas reciente con datos" es mas util que forzar siempre al llamador a
    indicar un encounter, documentado aqui y en PENDIENTES_CLINICOS.md)."""
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)

    resolved_encounter_id = encounter_id
    if resolved_encounter_id is None:
        latest_stmt = (
            select(PeriodontalIndexEntry.encounter_id)
            .where(
                PeriodontalIndexEntry.clinic_id == clinic_id,
                PeriodontalIndexEntry.patient_id == patient_id,
                PeriodontalIndexEntry.is_active.is_(True),
            )
            .order_by(PeriodontalIndexEntry.created_at.desc())
            .limit(1)
        )
        resolved_encounter_id = (await db.execute(latest_stmt)).scalars().first()

    placa_grades: list[int] = []
    gingival_grades: list[int] = []
    if resolved_encounter_id is not None:
        stmt = select(PeriodontalIndexEntry).where(
            PeriodontalIndexEntry.clinic_id == clinic_id,
            PeriodontalIndexEntry.patient_id == patient_id,
            PeriodontalIndexEntry.encounter_id == resolved_encounter_id,
            PeriodontalIndexEntry.is_active.is_(True),
        )
        entries = (await db.execute(stmt)).scalars().all()
        placa_grades = [e.grade for e in entries if e.index_type == "placa"]
        gingival_grades = [e.grade for e in entries if e.index_type == "gingival"]

    total_placa, pigmented, plaque_index = rules.compute_plaque_index(placa_grades)
    total_gingival, gingival_index = rules.compute_gingival_index(gingival_grades)

    return IndicesSummaryOut(
        encounter_id=resolved_encounter_id,
        placa=PlaqueIndexSummary(
            numero_caras_totales=total_placa,
            numero_caras_pigmentadas=pigmented,
            indice_placa_dentobacteriana=plaque_index,
        ),
        gingival=GingivalIndexSummary(
            numero_sitios_totales=total_gingival,
            indice_gingival_total=gingival_index,
        ),
    )


# --------------------------------------------------------------------------------
# 4. Tablas de oclusion -- contactos marcados.
# --------------------------------------------------------------------------------


async def list_occlusal_contacts(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[OcclusalContactEntry]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(OcclusalContactEntry)
        .where(
            OcclusalContactEntry.clinic_id == clinic_id,
            OcclusalContactEntry.patient_id == patient_id,
        )
        .order_by(OcclusalContactEntry.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_occlusal_contact(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: OcclusalContactEntryCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> OcclusalContactEntry:
    """Decision documentada en models.py: marcar de nuevo la MISMA
    pieza+movimiento en el MISMO encounter es idempotente -- no hay un
    "grado" que reemplazar, solo un estado de presencia, asi que se devuelve
    la fila activa existente en vez de crear un duplicado. Para "desmarcar"
    un contacto se usa el endpoint de anulacion."""
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    _check_tooth_code(data.tooth_fdi)

    existing_stmt = select(OcclusalContactEntry).where(
        OcclusalContactEntry.clinic_id == clinic_id,
        OcclusalContactEntry.patient_id == patient_id,
        OcclusalContactEntry.encounter_id == data.encounter_id,
        OcclusalContactEntry.tooth_fdi == data.tooth_fdi,
        OcclusalContactEntry.movement == data.movement,
        OcclusalContactEntry.is_active.is_(True),
    )
    existing = (await db.execute(existing_stmt)).scalars().first()
    if existing is not None:
        return existing

    item = OcclusalContactEntry(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        tooth_fdi=data.tooth_fdi,
        movement=data.movement,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="periodontogram.occlusal_contact_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="occlusal_contact_entry",
        entity_id=str(item.id),
        details={
            "patient_id": str(patient_id),
            "tooth_fdi": data.tooth_fdi,
            "movement": data.movement,
        },
    )
    await db.commit()
    return item


async def annul_occlusal_contact(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> OcclusalContactEntry:
    item = await db.get(OcclusalContactEntry, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Contacto oclusal no encontrado", status_code=404)
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="periodontogram.occlusal_contact_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="occlusal_contact_entry",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# 5. Observaciones del periodontograma.
# --------------------------------------------------------------------------------


async def list_observations(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[PeriodontogramObservation]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(PeriodontogramObservation)
        .where(
            PeriodontogramObservation.clinic_id == clinic_id,
            PeriodontogramObservation.patient_id == patient_id,
        )
        .order_by(PeriodontogramObservation.created_at.desc())
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_observation(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    data: PeriodontogramObservationCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> PeriodontogramObservation:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    item = PeriodontogramObservation(
        clinic_id=clinic_id,
        patient_id=patient_id,
        encounter_id=data.encounter_id,
        observaciones=data.observaciones,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()
    await audit_service.log(
        db,
        action="periodontogram.observation_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="periodontogram_observation",
        entity_id=str(item.id),
        details={"patient_id": str(patient_id)},
    )
    await db.commit()
    return item


async def annul_observation(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> PeriodontogramObservation:
    item = await db.get(PeriodontogramObservation, item_id)
    if item is None or item.clinic_id != clinic_id or item.patient_id != patient_id:
        raise AppError(
            "NOT_FOUND", "Observacion del periodontograma no encontrada", status_code=404
        )
    _annul(item, data, actor_id)
    await audit_service.log(
        db,
        action="periodontogram.observation_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="periodontogram_observation",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


# --------------------------------------------------------------------------------
# PDF.
# --------------------------------------------------------------------------------


async def generate_periodontogram_pdf(
    db: AsyncSession,
    storage: StorageBackend,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> bytes:
    """Periodontograma completo en PDF: la cuadricula de sondeo por pieza/
    sitio representada como TABLA de datos (no se replica el dibujo grafico
    del odontograma dentro de este PDF -- decision documentada, es aceptable
    una tabla clara, mismo criterio que el odontograma de endodoncia de la
    Fase F listado como texto), movilidad/furcacion por pieza, los indices
    calculados (encounter mas reciente con datos), las tablas de oclusion y
    las observaciones. Lista TODAS las filas activas del paciente (sin
    filtrar por un solo encounter), mismo criterio que
    pediatric_history/endodontic_history."""
    patient = await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    header = await get_pdf_header_info(db, storage, clinic_id=clinic_id)

    probing_sites = [
        item
        for item in await list_probing_sites(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    tooth_measurements = [
        item
        for item in await list_tooth_measurements(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    index_entries = [
        item
        for item in await list_index_entries(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    occlusal_contacts = [
        item
        for item in await list_occlusal_contacts(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    observations = [
        item
        for item in await list_observations(db, clinic_id=clinic_id, patient_id=patient_id)
        if item.is_active
    ]
    indices_summary = await get_indices_summary(db, clinic_id=clinic_id, patient_id=patient_id)

    def _bool_label(value: bool) -> str:
        return "Si" if value else "No"

    def _probing_row(item: PeriodontalProbingSite) -> str:
        site_label = rules.PROBING_SITE_LABELS.get(item.site, item.site)
        cal = rules.clinical_attachment_level_mm(item.probing_depth_mm, item.recession_mm)
        return (
            f"Pieza {item.tooth_fdi} - {site_label}: profundidad {item.probing_depth_mm} mm, "
            f"recesion {item.recession_mm} mm, NIC {cal} mm, "
            f"sangrado al sondaje: {_bool_label(item.bleeding_on_probing)}, "
            f"supuracion: {_bool_label(item.suppuration)}"
        )

    def _tooth_measurement_row(item: PeriodontalToothMeasurement) -> str:
        mobility = item.mobility_grade if item.mobility_grade is not None else "-"
        furcation = item.furcation_grade if item.furcation_grade is not None else "-"
        return f"Pieza {item.tooth_fdi}: movilidad grado {mobility}, furcacion grado {furcation}"

    def _index_row(item: PeriodontalIndexEntry) -> str:
        surface_label = rules.INDEX_SURFACE_LABELS.get(item.surface, item.surface)
        labels = (
            rules.PLAQUE_GRADE_LABELS if item.index_type == "placa" else rules.GINGIVAL_GRADE_LABELS
        )
        grade_label = labels.get(item.grade, str(item.grade))
        return f"Pieza {item.tooth_fdi} - {surface_label}: grado {item.grade} ({grade_label})"

    occlusal_rows = []
    for movement in rules.OCCLUSAL_MOVEMENTS:
        teeth = sorted({item.tooth_fdi for item in occlusal_contacts if item.movement == movement})
        movement_label = rules.OCCLUSAL_MOVEMENT_LABELS.get(movement, movement)
        teeth_label = ", ".join(teeth) if teeth else "Sin contactos marcados"
        occlusal_rows.append(f"{movement_label}: {teeth_label}")

    plaque = indices_summary.placa
    gingival = indices_summary.gingival
    plaque_index_label = (
        "-" if plaque.indice_placa_dentobacteriana is None else plaque.indice_placa_dentobacteriana
    )
    gingival_index_label = (
        "-" if gingival.indice_gingival_total is None else gingival.indice_gingival_total
    )
    plaque_summary_row = (
        f"Caras totales: {plaque.numero_caras_totales}, "
        f"caras con placa: {plaque.numero_caras_pigmentadas}, "
        f"indice de placa dentobacteriana: {plaque_index_label}"
    )
    gingival_summary_row = (
        f"Sitios totales: {gingival.numero_sitios_totales}, "
        f"indice gingival total: {gingival_index_label}"
    )

    data = PeriodontogramPdfData(
        header=header,
        date_label=datetime.now(UTC).strftime("%d/%m/%Y"),
        patient_full_name=patient.full_name,
        patient_expediente_number=patient.expediente_number,
        probing_rows=[_probing_row(item) for item in probing_sites],
        tooth_measurement_rows=[_tooth_measurement_row(item) for item in tooth_measurements],
        plaque_index_rows=[
            _index_row(item) for item in index_entries if item.index_type == "placa"
        ],
        gingival_index_rows=[
            _index_row(item) for item in index_entries if item.index_type == "gingival"
        ],
        plaque_summary_row=plaque_summary_row,
        gingival_summary_row=gingival_summary_row,
        occlusal_rows=occlusal_rows,
        observaciones_rows=[item.observaciones for item in observations if item.observaciones],
    )

    pdf_bytes = build_periodontogram_pdf(data)

    await audit_service.log(
        db,
        action="periodontogram.pdf_read",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="patient",
        entity_id=str(patient_id),
    )
    await db.commit()
    return pdf_bytes
