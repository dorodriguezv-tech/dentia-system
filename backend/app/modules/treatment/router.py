import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_clinic_id, require_permission
from app.core.storage import StorageBackend, get_storage_backend
from app.modules.branding import service as branding_service
from app.modules.iam.models import User
from app.modules.patients.models import Patient
from app.modules.treatment import service
from app.modules.treatment.pdf import BudgetItemRow, BudgetPhaseRow, build_budget_pdf
from app.modules.treatment.schemas import (
    AcceptPlanRequest,
    AnnulRequest,
    DiscountRequest,
    ItemCreateRequest,
    ItemOut,
    PhaseCreateRequest,
    PhaseWithItemsOut,
    PlanCreateRequest,
    PlanDetailOut,
    PlanOut,
    ProcedureCatalogCreateRequest,
    ProcedureCatalogOut,
    ProcedurePerformedCreateRequest,
    ProcedurePerformedOut,
    StatusChangeRequest,
)

router = APIRouter(tags=["treatment"])

PLAN_STATUS_LABELS = {
    "BORRADOR": "Borrador",
    "PRESENTADO": "Presentado",
    "ACEPTADO": "Aceptado",
    "RECHAZADO": "Rechazado",
    "EN_PROGRESO": "En progreso",
    "TERMINADO": "Terminado",
}


def _item_out(item) -> ItemOut:  # type: ignore[no-untyped-def]
    return ItemOut(
        id=item.id,
        phase_id=item.phase_id,
        encounter_id=item.encounter_id,
        tooth_fdi=item.tooth_fdi,
        surface=item.surface,
        procedure_code=item.procedure_code,
        procedure_name=item.procedure_name,
        finding_code=item.finding_code,
        unit_price=item.unit_price,
        quantity=item.quantity,
        alternative=item.alternative,
        discount_amount=item.discount_amount,
        discount_reason=item.discount_reason,
        accepted=item.accepted,
        is_active=item.is_active,
        subtotal=service.item_subtotal(item),
    )


def _plan_out(plan, total) -> PlanOut:  # type: ignore[no-untyped-def]
    return PlanOut(
        id=plan.id,
        patient_id=plan.patient_id,
        encounter_id=plan.encounter_id,
        professional_id=plan.professional_id,
        title=plan.title,
        status=plan.status,
        notes=plan.notes,
        accepted_at=plan.accepted_at,
        accepted_by_name=plan.accepted_by_name,
        acceptance_type=plan.acceptance_type,
        rejected_reason=plan.rejected_reason,
        total=total,
    )


@router.get("/procedure-catalog", response_model=list[ProcedureCatalogOut])
async def list_procedure_catalog(
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("treatment.read")),
    db: AsyncSession = Depends(get_db),
) -> list[ProcedureCatalogOut]:
    items = await service.list_procedure_catalog(db, clinic_id=clinic_id)
    return [ProcedureCatalogOut.model_validate(i) for i in items]


@router.post("/procedure-catalog", response_model=ProcedureCatalogOut, status_code=201)
async def create_procedure_catalog_item(
    payload: ProcedureCatalogCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("treatment.write")),
    db: AsyncSession = Depends(get_db),
) -> ProcedureCatalogOut:
    item = await service.create_procedure_catalog_item(
        db, clinic_id=clinic_id, data=payload, actor_id=actor.id
    )
    return ProcedureCatalogOut.model_validate(item)


@router.get("/patients/{patient_id}/treatment-plans", response_model=list[PlanOut])
async def list_plans(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("treatment.read")),
    db: AsyncSession = Depends(get_db),
) -> list[PlanOut]:
    rows = await service.list_plans(db, clinic_id=clinic_id, patient_id=patient_id)
    return [_plan_out(plan, total) for plan, total in rows]


@router.post("/treatment-plans", response_model=PlanOut, status_code=201)
async def create_plan(
    payload: PlanCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("treatment.write")),
    db: AsyncSession = Depends(get_db),
) -> PlanOut:
    plan = await service.create_plan(db, clinic_id=clinic_id, data=payload, actor_id=actor.id)
    return _plan_out(plan, Decimal("0"))


@router.get("/treatment-plans/{plan_id}", response_model=PlanDetailOut)
async def get_plan_detail(
    plan_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("treatment.read")),
    db: AsyncSession = Depends(get_db),
) -> PlanDetailOut:
    plan, phases = await service.get_plan_detail(db, clinic_id=clinic_id, plan_id=plan_id)
    phase_outs = []
    grand_total = Decimal("0")
    for phase, items in phases:
        item_outs = [_item_out(i) for i in items]
        phase_total = sum((i.subtotal for i in item_outs), Decimal("0"))
        grand_total += phase_total
        phase_outs.append(
            PhaseWithItemsOut(
                id=phase.id,
                name=phase.name,
                sort_order=phase.sort_order,
                priority=phase.priority,
                items=item_outs,
                phase_total=phase_total,
            )
        )
    return PlanDetailOut(
        id=plan.id,
        patient_id=plan.patient_id,
        encounter_id=plan.encounter_id,
        professional_id=plan.professional_id,
        title=plan.title,
        status=plan.status,
        notes=plan.notes,
        accepted_at=plan.accepted_at,
        accepted_by_name=plan.accepted_by_name,
        acceptance_type=plan.acceptance_type,
        rejected_reason=plan.rejected_reason,
        phases=phase_outs,
        total=grand_total,
    )


@router.patch("/treatment-plans/{plan_id}/status", response_model=PlanOut)
async def change_status(
    plan_id: uuid.UUID,
    payload: StatusChangeRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("treatment.write")),
    db: AsyncSession = Depends(get_db),
) -> PlanOut:
    plan = await service.change_status(
        db, clinic_id=clinic_id, plan_id=plan_id, data=payload, actor_id=actor.id
    )
    total = await service.plan_total(db, plan_id=plan.id)
    return _plan_out(plan, total)


@router.post("/treatment-plans/{plan_id}/accept", response_model=PlanOut)
async def accept_plan(
    plan_id: uuid.UUID,
    payload: AcceptPlanRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("treatment.accept_budget")),
    db: AsyncSession = Depends(get_db),
) -> PlanOut:
    plan = await service.accept_plan(
        db, clinic_id=clinic_id, plan_id=plan_id, data=payload, actor_id=actor.id
    )
    total = await service.plan_total(db, plan_id=plan.id)
    return _plan_out(plan, total)


@router.post("/treatment-plans/{plan_id}/phases", response_model=PhaseWithItemsOut, status_code=201)
async def add_phase(
    plan_id: uuid.UUID,
    payload: PhaseCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("treatment.write")),
    db: AsyncSession = Depends(get_db),
) -> PhaseWithItemsOut:
    phase = await service.add_phase(
        db, clinic_id=clinic_id, plan_id=plan_id, data=payload, actor_id=actor.id
    )
    return PhaseWithItemsOut(
        id=phase.id,
        name=phase.name,
        sort_order=phase.sort_order,
        priority=phase.priority,
        items=[],
        phase_total=Decimal("0"),
    )


@router.post(
    "/treatment-plans/{plan_id}/phases/{phase_id}/items", response_model=ItemOut, status_code=201
)
async def add_item(
    plan_id: uuid.UUID,
    phase_id: uuid.UUID,
    payload: ItemCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("treatment.write")),
    db: AsyncSession = Depends(get_db),
) -> ItemOut:
    item = await service.add_item(
        db,
        clinic_id=clinic_id,
        plan_id=plan_id,
        phase_id=phase_id,
        data=payload,
        actor_id=actor.id,
    )
    return _item_out(item)


@router.post("/treatment-plans/{plan_id}/items/{item_id}/annul", response_model=ItemOut)
async def annul_item(
    plan_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: AnnulRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("treatment.write")),
    db: AsyncSession = Depends(get_db),
) -> ItemOut:
    item = await service.annul_item(
        db,
        clinic_id=clinic_id,
        plan_id=plan_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return _item_out(item)


@router.post("/treatment-plans/{plan_id}/items/{item_id}/discount", response_model=ItemOut)
async def apply_discount(
    plan_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: DiscountRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("treatment.write")),
    db: AsyncSession = Depends(get_db),
) -> ItemOut:
    item = await service.apply_discount(
        db,
        clinic_id=clinic_id,
        plan_id=plan_id,
        item_id=item_id,
        data=payload,
        actor_id=actor.id,
    )
    return _item_out(item)


@router.post("/procedures-performed", response_model=ProcedurePerformedOut, status_code=201)
async def register_performed(
    payload: ProcedurePerformedCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("treatment.write")),
    db: AsyncSession = Depends(get_db),
) -> ProcedurePerformedOut:
    performed, charge_amount = await service.register_performed(
        db, clinic_id=clinic_id, data=payload, actor_id=actor.id
    )
    return ProcedurePerformedOut(
        id=performed.id,
        patient_id=performed.patient_id,
        encounter_id=performed.encounter_id,
        planned_id=performed.planned_id,
        tooth_fdi=performed.tooth_fdi,
        surface=performed.surface,
        procedure_code=performed.procedure_code,
        procedure_name=performed.procedure_name,
        material=performed.material,
        performed_at=performed.performed_at,
        charge_amount=charge_amount,
    )


@router.get(
    "/patients/{patient_id}/procedures-performed", response_model=list[ProcedurePerformedOut]
)
async def list_performed(
    patient_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("treatment.read")),
    db: AsyncSession = Depends(get_db),
) -> list[ProcedurePerformedOut]:
    rows = await service.list_performed(db, clinic_id=clinic_id, patient_id=patient_id)
    return [
        ProcedurePerformedOut(
            id=performed.id,
            patient_id=performed.patient_id,
            encounter_id=performed.encounter_id,
            planned_id=performed.planned_id,
            tooth_fdi=performed.tooth_fdi,
            surface=performed.surface,
            procedure_code=performed.procedure_code,
            procedure_name=performed.procedure_name,
            material=performed.material,
            performed_at=performed.performed_at,
            charge_amount=amount,
        )
        for performed, amount in rows
    ]


@router.get("/treatment-plans/{plan_id}/pdf")
async def get_plan_pdf(
    plan_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("treatment.read")),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage_backend),
) -> Response:
    plan, phases = await service.get_plan_detail(db, clinic_id=clinic_id, plan_id=plan_id)
    patient = await db.get(Patient, plan.patient_id)
    branding = await branding_service.get_branding(db)
    logo = await branding_service.read_logo(db, storage)

    phase_rows = []
    grand_total = Decimal("0")
    for phase, items in phases:
        item_rows = [
            BudgetItemRow(
                procedure_name=item.procedure_name,
                tooth_label=(
                    f"Pieza {item.tooth_fdi}" + (f" ({item.surface})" if item.surface else "")
                    if item.tooth_fdi
                    else "General"
                ),
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount=item.discount_amount,
                subtotal=service.item_subtotal(item),
            )
            for item in items
        ]
        phase_total = sum((row.subtotal for row in item_rows), Decimal("0"))
        grand_total += phase_total
        phase_rows.append(BudgetPhaseRow(name=phase.name, items=item_rows, phase_total=phase_total))

    acceptance_label = None
    if plan.accepted_at is not None:
        acceptance_label = (
            f"Aceptado ({plan.acceptance_type}) por {plan.accepted_by_name} "
            f"el {plan.accepted_at.strftime('%d/%m/%Y')}"
        )
    elif plan.status == "RECHAZADO" and plan.rejected_reason:
        acceptance_label = f"Rechazado: {plan.rejected_reason}"

    pdf_bytes = build_budget_pdf(
        clinic_name=branding.display_name,
        primary_color_hex=branding.colors.primary,
        logo=logo,
        patient_name=patient.full_name if patient else "",
        plan_title=plan.title,
        plan_status_label=PLAN_STATUS_LABELS[plan.status],
        created_at_label=plan.created_at.strftime("%d/%m/%Y"),
        phases=phase_rows,
        grand_total=grand_total,
        acceptance_label=acceptance_label,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="presupuesto-{plan_id}.pdf"'},
    )
