import uuid
from datetime import UTC, date, datetime, time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import AppError
from app.modules.catalogs import service as catalogs_service
from app.modules.encounters.models import Encounter
from app.modules.iam.models import User
from app.modules.odontogram import rules
from app.modules.odontogram.models import ToothFinding
from app.modules.odontogram.schemas import ToothFindingCreateRequest
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


def _normalize_surface(surface: str | None) -> str:
    return surface or ""


async def create_finding(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    data: ToothFindingCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> ToothFinding:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=data.patient_id)
    encounter = await _get_encounter_in_clinic(
        db, clinic_id=clinic_id, encounter_id=data.encounter_id
    )
    if encounter.patient_id != data.patient_id:
        raise AppError(
            "ENCOUNTER_PATIENT_MISMATCH",
            "La atencion no pertenece a este paciente",
            status_code=400,
        )

    if not rules.is_valid_tooth(data.tooth_fdi):
        raise AppError("INVALID_TOOTH", f"Pieza FDI invalida: {data.tooth_fdi}", status_code=422)
    if not rules.is_valid_surface_for_tooth(data.tooth_fdi, data.surface):
        raise AppError(
            "INVALID_SURFACE",
            f"La superficie {data.surface} no es valida para la pieza {data.tooth_fdi}",
            status_code=422,
        )

    # B1 (Parte B, Fase 12.2): "Hallazgos del odontograma" ya no es un diccionario fijo
    # en codigo -- valida contra el catalogo administrable de la sucursal y, si ese
    # hallazgo esta marcado como "requiere superficie" (nuevo: antes la superficie
    # siempre era opcional sin importar el hallazgo), exige que la peticion traiga una.
    findings = await catalogs_service.list_items(
        db, clinic_id=clinic_id, catalog_type="odontogram_finding"
    )
    finding_item = next((f for f in findings if f.code == data.finding_code), None)
    if finding_item is None:
        raise AppError(
            "INVALID_FINDING_CODE",
            "El hallazgo no existe o esta desactivado en esta sucursal",
            status_code=400,
        )
    if finding_item.extra.get("requires_surface") and data.surface is None:
        raise AppError(
            "SURFACE_REQUIRED",
            f"El hallazgo '{finding_item.name}' exige indicar una superficie",
            status_code=422,
        )

    current_stmt = select(ToothFinding).where(
        ToothFinding.clinic_id == clinic_id,
        ToothFinding.patient_id == data.patient_id,
        ToothFinding.tooth_fdi == data.tooth_fdi,
        ToothFinding.kind == data.kind,
        ToothFinding.is_current.is_(True),
        func.coalesce(ToothFinding.surface, "") == _normalize_surface(data.surface),
    )
    previous = (await db.execute(current_stmt)).scalar_one_or_none()
    if previous is not None:
        previous.is_current = False

    item = ToothFinding(
        clinic_id=clinic_id,
        patient_id=data.patient_id,
        encounter_id=data.encounter_id,
        tooth_fdi=data.tooth_fdi,
        surface=data.surface,
        finding_code=data.finding_code,
        kind=data.kind,
        material=data.material,
        supersedes_id=previous.id if previous else None,
        is_current=True,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()

    await audit_service.log(
        db,
        action="odontogram.finding_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="tooth_finding",
        entity_id=str(item.id),
        details={
            "patient_id": str(data.patient_id),
            "tooth_fdi": data.tooth_fdi,
            "surface": data.surface,
            "finding_code": data.finding_code,
            "kind": data.kind,
        },
    )
    await db.commit()
    return item


async def get_current_odontogram(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[ToothFinding]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = select(ToothFinding).where(
        ToothFinding.clinic_id == clinic_id,
        ToothFinding.patient_id == patient_id,
        ToothFinding.is_current.is_(True),
    )
    return list((await db.execute(stmt)).scalars().all())


async def get_odontogram_at(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID, at: date
) -> list[ToothFinding]:
    """Reconstruye el estado del odontograma a una fecha (regla 5): para cada
    (pieza, superficie, tipo) toma el evento mas reciente que ya existia a esa fecha."""
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    cutoff = datetime.combine(at, time.max, tzinfo=UTC)
    stmt = (
        select(ToothFinding)
        .where(
            ToothFinding.clinic_id == clinic_id,
            ToothFinding.patient_id == patient_id,
            ToothFinding.created_at <= cutoff,
        )
        .order_by(ToothFinding.created_at)
    )
    rows = (await db.execute(stmt)).scalars().all()

    latest: dict[tuple[int, str, str], ToothFinding] = {}
    for row in rows:
        key = (row.tooth_fdi, _normalize_surface(row.surface), row.kind)
        latest[key] = row  # ordenados por created_at asc: el ultimo en el loop gana
    return list(latest.values())


async def get_tooth_history(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID, tooth_fdi: int
) -> list[tuple[ToothFinding, str]]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(ToothFinding)
        .where(
            ToothFinding.clinic_id == clinic_id,
            ToothFinding.patient_id == patient_id,
            ToothFinding.tooth_fdi == tooth_fdi,
        )
        .order_by(ToothFinding.created_at.desc())
    )
    rows = list((await db.execute(stmt)).scalars().all())

    author_ids = {row.created_by for row in rows if row.created_by is not None}
    authors: dict[uuid.UUID, str] = {}
    if author_ids:
        users = (await db.execute(select(User).where(User.id.in_(author_ids)))).scalars().all()
        authors = {u.id: u.full_name for u in users}

    return [(row, authors.get(row.created_by, "") if row.created_by else "") for row in rows]


async def retire_finding(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    finding_id: uuid.UUID,
    actor_id: uuid.UUID,
) -> ToothFinding:
    """Deshace una captura ya aplicada (docs/05_ASISTENTE_DENTIA_VOZ_CONVERSACIONAL.md
    sec. 6.5, "deshaz" de Dentia -- Fase 13.3): nunca borra (regla 2 de
    CLAUDE.md) -- marca el hallazgo como no vigente y, si remplazaba a uno
    anterior, lo reactiva, dejando el odontograma como antes de la captura."""
    finding = await db.get(ToothFinding, finding_id)
    if finding is None or finding.clinic_id != clinic_id or finding.patient_id != patient_id:
        raise AppError("NOT_FOUND", "Hallazgo no encontrado", status_code=404)
    if not finding.is_current:
        raise AppError("FINDING_NOT_CURRENT", "Ese hallazgo ya no esta vigente", status_code=409)

    finding.is_current = False
    if finding.supersedes_id is not None:
        previous = await db.get(ToothFinding, finding.supersedes_id)
        if previous is not None:
            previous.is_current = True

    await audit_service.log(
        db,
        action="odontogram.finding_retired",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="tooth_finding",
        entity_id=str(finding.id),
        details={
            "patient_id": str(patient_id),
            "tooth_fdi": finding.tooth_fdi,
            "surface": finding.surface,
        },
    )
    await db.commit()
    return finding


async def retire_planned(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    patient_id: uuid.UUID,
    tooth_fdi: int,
    surface: str | None,
) -> None:
    """Retira (is_current=False) el hallazgo PLANNED vigente de esa pieza/superficie
    sin crear un evento nuevo (regla 3 de CLAUDE.md: lo planificado ya no aplica
    porque se realizo; el nuevo PERFORMED/EXISTING es quien ahora refleja el estado
    real). No hace commit: participa de la transaccion de quien la llama
    (treatment.service al registrar un ProcedurePerformed)."""
    stmt = select(ToothFinding).where(
        ToothFinding.clinic_id == clinic_id,
        ToothFinding.patient_id == patient_id,
        ToothFinding.tooth_fdi == tooth_fdi,
        ToothFinding.kind == "PLANNED",
        ToothFinding.is_current.is_(True),
        func.coalesce(ToothFinding.surface, "") == _normalize_surface(surface),
    )
    planned = (await db.execute(stmt)).scalar_one_or_none()
    if planned is not None:
        planned.is_current = False
