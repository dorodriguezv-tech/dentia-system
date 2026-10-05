import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import AppError
from app.modules.billing import service as billing_service
from app.modules.encounters.models import Encounter
from app.modules.odontogram import rules as odontogram_rules
from app.modules.odontogram import service as odontogram_service
from app.modules.odontogram.schemas import ToothFindingCreateRequest
from app.modules.patients.models import Patient
from app.modules.treatment import rules
from app.modules.treatment.models import (
    ProcedureCatalog,
    ProcedurePerformed,
    ProcedurePlanned,
    TreatmentPhase,
    TreatmentPlan,
)
from app.modules.treatment.schemas import (
    AcceptPlanRequest,
    AnnulRequest,
    DiscountRequest,
    ItemCreateRequest,
    PhaseCreateRequest,
    PlanCreateRequest,
    ProcedureCatalogCreateRequest,
    ProcedurePerformedCreateRequest,
    StatusChangeRequest,
)


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


async def _get_plan_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, plan_id: uuid.UUID
) -> TreatmentPlan:
    plan = await db.get(TreatmentPlan, plan_id)
    if plan is None or plan.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Plan de tratamiento no encontrado", status_code=404)
    return plan


async def _get_phase_in_plan(
    db: AsyncSession, *, plan_id: uuid.UUID, phase_id: uuid.UUID
) -> TreatmentPhase:
    phase = await db.get(TreatmentPhase, phase_id)
    if phase is None or phase.plan_id != plan_id:
        raise AppError("NOT_FOUND", "Fase no encontrada", status_code=404)
    return phase


async def _get_catalog_item(
    db: AsyncSession, *, clinic_id: uuid.UUID, code: str
) -> ProcedureCatalog:
    stmt = select(ProcedureCatalog).where(
        ProcedureCatalog.clinic_id == clinic_id, ProcedureCatalog.code == code
    )
    item = (await db.execute(stmt)).scalar_one_or_none()
    if item is None:
        raise AppError(
            "NOT_FOUND", f"El procedimiento '{code}' no esta en el catalogo", status_code=404
        )
    return item


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


def item_subtotal(item: ProcedurePlanned) -> Decimal:
    subtotal = item.unit_price * item.quantity
    if item.discount_amount:
        subtotal -= item.discount_amount
    return subtotal


# --------------------------------------------------------------- catalogo de procedimientos


async def list_procedure_catalog(
    db: AsyncSession, *, clinic_id: uuid.UUID
) -> list[ProcedureCatalog]:
    stmt = select(ProcedureCatalog).where(ProcedureCatalog.clinic_id == clinic_id)
    return list((await db.execute(stmt)).scalars().all())


async def create_procedure_catalog_item(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    data: ProcedureCatalogCreateRequest,
    actor_id: uuid.UUID,
) -> ProcedureCatalog:
    item = ProcedureCatalog(
        clinic_id=clinic_id,
        code=data.code,
        name=data.name,
        default_price=data.default_price,
        created_by=actor_id,
    )
    db.add(item)
    await db.commit()
    return item


# --------------------------------------------------------------------------- planes


async def create_plan(
    db: AsyncSession, *, clinic_id: uuid.UUID, data: PlanCreateRequest, actor_id: uuid.UUID
) -> TreatmentPlan:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=data.patient_id)
    await _get_encounter_in_clinic(db, clinic_id=clinic_id, encounter_id=data.encounter_id)

    plan = TreatmentPlan(
        clinic_id=clinic_id,
        patient_id=data.patient_id,
        encounter_id=data.encounter_id,
        professional_id=actor_id,
        title=data.title,
        status="BORRADOR",
        notes=data.notes,
        created_by=actor_id,
    )
    db.add(plan)
    await db.flush()
    await audit_service.log(
        db,
        action="treatment.plan_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="treatment_plan",
        entity_id=str(plan.id),
        details={"patient_id": str(data.patient_id), "title": data.title},
    )
    await db.commit()
    return plan


async def _plan_items(db: AsyncSession, *, plan_id: uuid.UUID) -> list[ProcedurePlanned]:
    stmt = select(ProcedurePlanned).where(
        ProcedurePlanned.plan_id == plan_id, ProcedurePlanned.is_active.is_(True)
    )
    return list((await db.execute(stmt)).scalars().all())


async def plan_total(db: AsyncSession, *, plan_id: uuid.UUID) -> Decimal:
    items = await _plan_items(db, plan_id=plan_id)
    return sum((item_subtotal(i) for i in items), Decimal("0"))


async def list_plans(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[tuple[TreatmentPlan, Decimal]]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(TreatmentPlan)
        .where(TreatmentPlan.clinic_id == clinic_id, TreatmentPlan.patient_id == patient_id)
        .order_by(TreatmentPlan.created_at.desc())
    )
    plans = list((await db.execute(stmt)).scalars().all())
    return [(plan, await plan_total(db, plan_id=plan.id)) for plan in plans]


async def get_plan_detail(
    db: AsyncSession, *, clinic_id: uuid.UUID, plan_id: uuid.UUID
) -> tuple[TreatmentPlan, list[tuple[TreatmentPhase, list[ProcedurePlanned]]]]:
    plan = await _get_plan_in_clinic(db, clinic_id=clinic_id, plan_id=plan_id)
    phases_stmt = (
        select(TreatmentPhase)
        .where(TreatmentPhase.plan_id == plan_id)
        .order_by(TreatmentPhase.sort_order)
    )
    phases = list((await db.execute(phases_stmt)).scalars().all())
    result = []
    for phase in phases:
        items_stmt = (
            select(ProcedurePlanned)
            .where(ProcedurePlanned.phase_id == phase.id, ProcedurePlanned.is_active.is_(True))
            .order_by(ProcedurePlanned.created_at)
        )
        items = list((await db.execute(items_stmt)).scalars().all())
        result.append((phase, items))
    return plan, result


async def change_status(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    plan_id: uuid.UUID,
    data: StatusChangeRequest,
    actor_id: uuid.UUID,
) -> TreatmentPlan:
    plan = await _get_plan_in_clinic(db, clinic_id=clinic_id, plan_id=plan_id)
    if not rules.can_transition(plan.status, data.status):
        raise AppError(
            "INVALID_TRANSITION",
            f"No se puede pasar de {plan.status} a {data.status}",
            status_code=409,
        )
    if data.status == "RECHAZADO" and not data.reason:
        raise AppError("REASON_REQUIRED", "Rechazar un plan exige un motivo", status_code=422)

    from_status = plan.status
    plan.status = data.status
    if data.status == "RECHAZADO":
        plan.rejected_reason = data.reason

    await audit_service.log(
        db,
        action="treatment.plan_status_changed",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="treatment_plan",
        entity_id=str(plan.id),
        details={"from": from_status, "to": data.status, "reason": data.reason},
    )
    await db.commit()
    return plan


async def accept_plan(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    plan_id: uuid.UUID,
    data: AcceptPlanRequest,
    actor_id: uuid.UUID,
) -> TreatmentPlan:
    plan = await _get_plan_in_clinic(db, clinic_id=clinic_id, plan_id=plan_id)
    if not rules.can_transition(plan.status, "ACEPTADO"):
        raise AppError(
            "INVALID_TRANSITION",
            f"No se puede aceptar un plan en estado {plan.status}",
            status_code=409,
        )

    items = await _plan_items(db, plan_id=plan_id)
    item_ids = {item.id for item in items}
    accepted_ids = set(data.accepted_item_ids)
    unknown_ids = accepted_ids - item_ids
    if unknown_ids:
        raise AppError(
            "NOT_FOUND",
            "Algunos procedimientos aceptados no pertenecen a este plan",
            status_code=404,
        )

    for item in items:
        item.accepted = item.id in accepted_ids

    plan.status = "ACEPTADO"
    plan.accepted_at = datetime.now(UTC)
    plan.accepted_by = actor_id
    plan.accepted_by_name = data.accepted_by_name
    plan.acceptance_type = "TOTAL" if accepted_ids == item_ids else "PARCIAL"

    await audit_service.log(
        db,
        action="treatment.plan_accepted",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="treatment_plan",
        entity_id=str(plan.id),
        details={
            "acceptance_type": plan.acceptance_type,
            "accepted_item_ids": [str(i) for i in accepted_ids],
            "accepted_by_name": data.accepted_by_name,
        },
    )
    await db.commit()
    return plan


# --------------------------------------------------------------------------- fases


async def add_phase(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    plan_id: uuid.UUID,
    data: PhaseCreateRequest,
    actor_id: uuid.UUID,
) -> TreatmentPhase:
    plan = await _get_plan_in_clinic(db, clinic_id=clinic_id, plan_id=plan_id)
    if not rules.is_editable(plan.status):
        raise AppError(
            "PLAN_NOT_EDITABLE",
            "Solo se pueden agregar fases mientras el plan esta en borrador",
            status_code=403,
        )
    phase = TreatmentPhase(
        plan_id=plan_id,
        name=data.name,
        sort_order=data.sort_order,
        priority=data.priority,
        created_by=actor_id,
    )
    db.add(phase)
    await db.commit()
    return phase


# ---------------------------------------------------------------------------- items


async def add_item(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    plan_id: uuid.UUID,
    phase_id: uuid.UUID,
    data: ItemCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> ProcedurePlanned:
    plan = await _get_plan_in_clinic(db, clinic_id=clinic_id, plan_id=plan_id)
    if not rules.is_editable(plan.status):
        raise AppError(
            "PLAN_NOT_EDITABLE",
            "Solo se pueden agregar procedimientos mientras el plan esta en borrador",
            status_code=403,
        )
    await _get_phase_in_plan(db, plan_id=plan_id, phase_id=phase_id)
    await _get_encounter_in_clinic(db, clinic_id=clinic_id, encounter_id=data.encounter_id)
    _validate_tooth_surface(data.tooth_fdi, data.surface)

    catalog_item = await _get_catalog_item(db, clinic_id=clinic_id, code=data.procedure_code)
    unit_price = (
        data.unit_price_override
        if data.unit_price_override is not None
        else catalog_item.default_price
    )

    item = ProcedurePlanned(
        clinic_id=clinic_id,
        plan_id=plan_id,
        phase_id=phase_id,
        patient_id=plan.patient_id,
        encounter_id=data.encounter_id,
        tooth_fdi=data.tooth_fdi,
        surface=data.surface,
        procedure_code=data.procedure_code,
        procedure_name=catalog_item.name,
        finding_code=data.finding_code,
        unit_price=unit_price,
        quantity=data.quantity,
        alternative=data.alternative,
        origin=origin,
        created_by=actor_id,
    )
    db.add(item)
    await db.flush()

    if data.tooth_fdi is not None and data.finding_code is not None:
        await odontogram_service.create_finding(
            db,
            clinic_id=clinic_id,
            data=ToothFindingCreateRequest(
                patient_id=plan.patient_id,
                encounter_id=data.encounter_id,
                tooth_fdi=data.tooth_fdi,
                surface=data.surface,
                finding_code=data.finding_code,
                kind="PLANNED",
            ),
            actor_id=actor_id,
            origin=origin,
        )

    await audit_service.log(
        db,
        action="treatment.item_planned",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="procedure_planned",
        entity_id=str(item.id),
        details={"plan_id": str(plan_id), "procedure_code": data.procedure_code},
    )
    await db.commit()
    return item


async def annul_item(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    plan_id: uuid.UUID,
    item_id: uuid.UUID,
    data: AnnulRequest,
    actor_id: uuid.UUID,
) -> ProcedurePlanned:
    item = await db.get(ProcedurePlanned, item_id)
    if item is None or item.clinic_id != clinic_id or item.plan_id != plan_id:
        raise AppError("NOT_FOUND", "Procedimiento planificado no encontrado", status_code=404)

    item.is_active = False
    item.annul_reason = data.reason
    item.annulled_by = actor_id
    item.annulled_at = datetime.now(UTC)

    if item.tooth_fdi is not None:
        await odontogram_service.retire_planned(
            db,
            clinic_id=clinic_id,
            patient_id=item.patient_id,
            tooth_fdi=item.tooth_fdi,
            surface=item.surface,
        )

    await audit_service.log(
        db,
        action="treatment.item_annulled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="procedure_planned",
        entity_id=str(item_id),
        details={"reason": data.reason},
    )
    await db.commit()
    return item


async def apply_discount(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    plan_id: uuid.UUID,
    item_id: uuid.UUID,
    data: DiscountRequest,
    actor_id: uuid.UUID,
) -> ProcedurePlanned:
    item = await db.get(ProcedurePlanned, item_id)
    if item is None or item.clinic_id != clinic_id or item.plan_id != plan_id:
        raise AppError("NOT_FOUND", "Procedimiento planificado no encontrado", status_code=404)
    if data.amount > item.unit_price * item.quantity:
        raise AppError(
            "INVALID_DISCOUNT", "El descuento no puede superar el subtotal", status_code=422
        )

    item.discount_amount = data.amount
    item.discount_reason = data.reason
    item.discount_authorized_by = actor_id

    await audit_service.log(
        db,
        action="treatment.discount_applied",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="procedure_planned",
        entity_id=str(item_id),
        details={"amount": str(data.amount), "reason": data.reason},
    )
    await db.commit()
    return item


# ----------------------------------------------------------------- procedimientos realizados


async def register_performed(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    data: ProcedurePerformedCreateRequest,
    actor_id: uuid.UUID,
    origin: str = "MANUAL",
) -> tuple[ProcedurePerformed, Decimal]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=data.patient_id)
    await _get_encounter_in_clinic(db, clinic_id=clinic_id, encounter_id=data.encounter_id)
    _validate_tooth_surface(data.tooth_fdi, data.surface)

    planned: ProcedurePlanned | None = None
    if data.planned_id is not None:
        planned = await db.get(ProcedurePlanned, data.planned_id)
        if (
            planned is None
            or planned.clinic_id != clinic_id
            or planned.patient_id != data.patient_id
        ):
            raise AppError("NOT_FOUND", "Procedimiento planificado no encontrado", status_code=404)

    tooth_fdi = (
        data.tooth_fdi if data.tooth_fdi is not None else (planned.tooth_fdi if planned else None)
    )
    surface = data.surface if data.surface is not None else (planned.surface if planned else None)
    procedure_code = data.procedure_code or (planned.procedure_code if planned else None)
    finding_code = data.finding_code or (planned.finding_code if planned else None)
    if procedure_code is None:
        raise AppError(
            "VALIDATION_ERROR",
            "Se necesita procedure_code (directo o a traves de planned_id)",
            status_code=422,
        )

    catalog_item = await _get_catalog_item(db, clinic_id=clinic_id, code=procedure_code)
    procedure_name = data.procedure_name or catalog_item.name
    charge_amount = item_subtotal(planned) if planned is not None else catalog_item.default_price

    performed = ProcedurePerformed(
        clinic_id=clinic_id,
        patient_id=data.patient_id,
        encounter_id=data.encounter_id,
        professional_id=actor_id,
        planned_id=data.planned_id,
        tooth_fdi=tooth_fdi,
        surface=surface,
        procedure_code=procedure_code,
        procedure_name=procedure_name,
        finding_code=finding_code,
        material=data.material,
        performed_at=datetime.now(UTC),
        origin=origin,
        created_by=actor_id,
    )
    db.add(performed)
    await db.flush()

    if tooth_fdi is not None and finding_code is not None:
        # PERFORMED dura como evento (regla 3); EXISTING se reemplaza porque el
        # estado clinico de la pieza de verdad cambio -- reutiliza el supersedes_id
        # de la Fase 5 para quedarse con un solo EXISTING vigente por pieza/superficie.
        for kind in ("PERFORMED", "EXISTING"):
            await odontogram_service.create_finding(
                db,
                clinic_id=clinic_id,
                data=ToothFindingCreateRequest(
                    patient_id=data.patient_id,
                    encounter_id=data.encounter_id,
                    tooth_fdi=tooth_fdi,
                    surface=surface,
                    finding_code=finding_code,
                    kind=kind,
                ),
                actor_id=actor_id,
                origin=origin,
            )
        if planned is not None:
            await odontogram_service.retire_planned(
                db,
                clinic_id=clinic_id,
                patient_id=data.patient_id,
                tooth_fdi=tooth_fdi,
                surface=surface,
            )

    charge = await billing_service.create_charge(
        db,
        clinic_id=clinic_id,
        patient_id=data.patient_id,
        procedure_performed_id=performed.id,
        amount=charge_amount,
        description=f"{procedure_name} ({performed.performed_at.date().isoformat()})",
        actor_id=actor_id,
    )

    await audit_service.log(
        db,
        action="treatment.procedure_performed",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="procedure_performed",
        entity_id=str(performed.id),
        details={
            "planned_id": str(data.planned_id) if data.planned_id else None,
            "procedure_code": procedure_code,
            "charge_id": str(charge.id),
        },
    )
    await db.commit()
    return performed, charge_amount


async def list_performed(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> list[tuple[ProcedurePerformed, Decimal]]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=patient_id)
    stmt = (
        select(ProcedurePerformed)
        .where(
            ProcedurePerformed.clinic_id == clinic_id, ProcedurePerformed.patient_id == patient_id
        )
        .order_by(ProcedurePerformed.performed_at.desc())
    )
    performed_list = list((await db.execute(stmt)).scalars().all())

    charges = await billing_service.list_charges(db, clinic_id=clinic_id, patient_id=patient_id)
    amount_by_performed_id = {c.procedure_performed_id: c.amount for c in charges}

    return [
        (performed, amount_by_performed_id.get(performed.id, Decimal("0")))
        for performed in performed_list
    ]
