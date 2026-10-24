import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import (
    get_clinic_id,
    get_current_user,
    require_permission,
    user_has_any_permission,
)
from app.core.errors import AppError
from app.modules.agenda import service
from app.modules.agenda.rules import DEFAULT_APPOINTMENT_DURATION_MINUTES
from app.modules.agenda.schemas import (
    AppointmentCreateRequest,
    AppointmentListItemOut,
    AppointmentOut,
    AvailableSlotsOut,
    BlockCreateRequest,
    BlockOut,
    DayScheduleOut,
    DayScheduleSlotOut,
    ProviderCreateRequest,
    ProviderOut,
    ReminderTaskOut,
    RescheduleRequest,
    ResourceCreateRequest,
    ResourceOut,
    ResourceUpdateRequest,
    StatusChangeRequest,
    WaitlistCreateRequest,
    WaitlistOut,
    WorkingHoursCreateRequest,
    WorkingHoursOut,
)
from app.modules.encounters.schemas import EncounterOut
from app.modules.iam.models import User

router = APIRouter(tags=["agenda"])


@router.get("/providers", response_model=list[ProviderOut])
async def list_providers(
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("agenda.read")),
    db: AsyncSession = Depends(get_db),
) -> list[ProviderOut]:
    rows = await service.list_providers(db, clinic_id=clinic_id)
    return [
        ProviderOut(
            id=p.id,
            user_id=p.user_id,
            full_name=name,
            color=p.color,
            is_active=p.is_active,
            default_resource_id=p.default_resource_id,
        )
        for p, name in rows
    ]


@router.post("/providers", response_model=ProviderOut, status_code=201)
async def create_provider(
    payload: ProviderCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("agenda.write")),
    db: AsyncSession = Depends(get_db),
) -> ProviderOut:
    provider, name = await service.create_provider(
        db, clinic_id=clinic_id, data=payload, actor_id=actor.id
    )
    return ProviderOut(
        id=provider.id,
        user_id=provider.user_id,
        full_name=name,
        color=provider.color,
        is_active=provider.is_active,
        default_resource_id=provider.default_resource_id,
    )


@router.get("/resources", response_model=list[ResourceOut])
async def list_resources(
    include_inactive: bool = Query(default=False),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ResourceOut]:
    allowed = await user_has_any_permission(
        db, user_id=current_user.id, clinic_id=clinic_id, codes=("agenda.read",)
    )
    if not allowed:
        raise AppError("FORBIDDEN", "No tienes permiso para esta accion", status_code=403)
    # Pendiente de B1 (Parte B, Fase 12.2): solo quien puede administrar gabinetes
    # (agenda.write) ve los inactivos -- igual que `catalogs.manage` con los
    # catalogos genericos.
    if include_inactive:
        can_manage = await user_has_any_permission(
            db, user_id=current_user.id, clinic_id=clinic_id, codes=("agenda.write",)
        )
        if not can_manage:
            include_inactive = False
    items = await service.list_resources(db, clinic_id=clinic_id, include_inactive=include_inactive)
    return [ResourceOut.model_validate(i) for i in items]


@router.post("/resources", response_model=ResourceOut, status_code=201)
async def create_resource(
    payload: ResourceCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("agenda.write")),
    db: AsyncSession = Depends(get_db),
) -> ResourceOut:
    item = await service.create_resource(db, clinic_id=clinic_id, data=payload, actor_id=actor.id)
    return ResourceOut.model_validate(item)


@router.patch("/resources/{resource_id}", response_model=ResourceOut)
async def update_resource(
    resource_id: uuid.UUID,
    payload: ResourceUpdateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("agenda.write")),
    db: AsyncSession = Depends(get_db),
) -> ResourceOut:
    item = await service.update_resource(
        db, clinic_id=clinic_id, resource_id=resource_id, data=payload, actor_id=actor.id
    )
    return ResourceOut.model_validate(item)


@router.get("/providers/{provider_id}/working-hours", response_model=list[WorkingHoursOut])
async def list_working_hours(
    provider_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("agenda.read")),
    db: AsyncSession = Depends(get_db),
) -> list[WorkingHoursOut]:
    items = await service.list_working_hours(db, clinic_id=clinic_id, provider_id=provider_id)
    return [WorkingHoursOut.model_validate(i) for i in items]


@router.post(
    "/providers/{provider_id}/working-hours", response_model=WorkingHoursOut, status_code=201
)
async def create_working_hours(
    provider_id: uuid.UUID,
    payload: WorkingHoursCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("agenda.write")),
    db: AsyncSession = Depends(get_db),
) -> WorkingHoursOut:
    item = await service.create_working_hours(
        db, clinic_id=clinic_id, provider_id=provider_id, data=payload
    )
    return WorkingHoursOut.model_validate(item)


@router.delete("/providers/{provider_id}/working-hours/{item_id}", status_code=204)
async def delete_working_hours(
    provider_id: uuid.UUID,
    item_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("agenda.write")),
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.delete_working_hours(
        db, clinic_id=clinic_id, provider_id=provider_id, item_id=item_id
    )


@router.get("/providers/{provider_id}/blocks", response_model=list[BlockOut])
async def list_blocks(
    provider_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("agenda.read")),
    db: AsyncSession = Depends(get_db),
) -> list[BlockOut]:
    items = await service.list_blocks(db, clinic_id=clinic_id, provider_id=provider_id)
    return [BlockOut.model_validate(i) for i in items]


@router.post("/providers/{provider_id}/blocks", response_model=BlockOut, status_code=201)
async def create_block(
    provider_id: uuid.UUID,
    payload: BlockCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("agenda.write")),
    db: AsyncSession = Depends(get_db),
) -> BlockOut:
    item = await service.create_block(
        db, clinic_id=clinic_id, provider_id=provider_id, data=payload, actor_id=actor.id
    )
    return BlockOut.model_validate(item)


@router.delete("/providers/{provider_id}/blocks/{item_id}", status_code=204)
async def delete_block(
    provider_id: uuid.UUID,
    item_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("agenda.write")),
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.delete_block(db, clinic_id=clinic_id, provider_id=provider_id, item_id=item_id)


@router.get("/appointments", response_model=list[AppointmentListItemOut])
async def list_appointments(
    starts_from: datetime = Query(...),
    starts_to: datetime = Query(...),
    provider_id: uuid.UUID | None = Query(default=None),
    resource_id: uuid.UUID | None = Query(default=None),
    patient_id: uuid.UUID | None = Query(default=None),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("agenda.read")),
    db: AsyncSession = Depends(get_db),
) -> list[AppointmentListItemOut]:
    items = await service.list_appointments(
        db,
        clinic_id=clinic_id,
        starts_from=starts_from,
        starts_to=starts_to,
        provider_id=provider_id,
        resource_id=resource_id,
        patient_id=patient_id,
    )
    return [AppointmentListItemOut(**i) for i in items]


@router.get("/appointments/availability", response_model=AvailableSlotsOut)
async def get_availability(
    provider_id: uuid.UUID = Query(...),
    day: date = Query(...),
    duration_minutes: int = Query(default=DEFAULT_APPOINTMENT_DURATION_MINUTES, ge=5, le=480),
    limit: int = Query(default=3, ge=1, le=20),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("agenda.read")),
    db: AsyncSession = Depends(get_db),
) -> AvailableSlotsOut:
    times = await service.find_free_slots(
        db,
        clinic_id=clinic_id,
        provider_id=provider_id,
        day=day,
        duration_minutes=duration_minutes,
        limit=limit,
    )
    return AvailableSlotsOut(slots=[datetime.combine(day, t, tzinfo=UTC) for t in times])


@router.get("/appointments/day-schedule", response_model=DayScheduleOut)
async def get_day_schedule(
    provider_id: uuid.UUID = Query(...),
    day: date = Query(...),
    duration_minutes: int = Query(default=DEFAULT_APPOINTMENT_DURATION_MINUTES, ge=5, le=480),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("agenda.read")),
    db: AsyncSession = Depends(get_db),
) -> DayScheduleOut:
    slots = await service.get_day_schedule(
        db,
        clinic_id=clinic_id,
        provider_id=provider_id,
        day=day,
        duration_minutes=duration_minutes,
    )
    return DayScheduleOut(
        slots=[
            DayScheduleSlotOut(starts_at=datetime.combine(day, t, tzinfo=UTC), available=available)
            for t, available in slots
        ]
    )


@router.post("/appointments", response_model=AppointmentOut, status_code=201)
async def create_appointment(
    payload: AppointmentCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("agenda.write")),
    db: AsyncSession = Depends(get_db),
) -> AppointmentOut:
    appointment, warnings = await service.create_appointment(
        db, clinic_id=clinic_id, data=payload, actor_id=actor.id
    )
    return AppointmentOut.model_validate(appointment).model_copy(update={"warnings": warnings})


@router.patch("/appointments/{appointment_id}/status", response_model=AppointmentOut)
async def change_status(
    appointment_id: uuid.UUID,
    payload: StatusChangeRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("agenda.write")),
    db: AsyncSession = Depends(get_db),
) -> AppointmentOut:
    appointment = await service.change_status(
        db, clinic_id=clinic_id, appointment_id=appointment_id, data=payload, actor_id=actor.id
    )
    return AppointmentOut.model_validate(appointment)


@router.post("/appointments/{appointment_id}/reschedule", response_model=AppointmentOut)
async def reschedule_appointment(
    appointment_id: uuid.UUID,
    payload: RescheduleRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("agenda.write")),
    db: AsyncSession = Depends(get_db),
) -> AppointmentOut:
    appointment, warnings = await service.reschedule_appointment(
        db, clinic_id=clinic_id, appointment_id=appointment_id, data=payload, actor_id=actor.id
    )
    return AppointmentOut.model_validate(appointment).model_copy(update={"warnings": warnings})


@router.post("/appointments/{appointment_id}/start-encounter", response_model=EncounterOut)
async def start_encounter(
    appointment_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("records.write")),
    db: AsyncSession = Depends(get_db),
) -> EncounterOut:
    encounter = await service.start_encounter_from_appointment(
        db, clinic_id=clinic_id, appointment_id=appointment_id, actor_id=actor.id
    )
    return EncounterOut.model_validate(encounter)


@router.get("/appointments/{appointment_id}/reminders", response_model=list[ReminderTaskOut])
async def list_reminders(
    appointment_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("agenda.read")),
    db: AsyncSession = Depends(get_db),
) -> list[ReminderTaskOut]:
    items = await service.list_reminder_tasks(
        db, clinic_id=clinic_id, appointment_id=appointment_id
    )
    return [ReminderTaskOut.model_validate(i) for i in items]


@router.get("/waitlist", response_model=list[WaitlistOut])
async def list_waitlist(
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("agenda.read")),
    db: AsyncSession = Depends(get_db),
) -> list[WaitlistOut]:
    items = await service.list_waitlist(db, clinic_id=clinic_id)
    return [WaitlistOut.model_validate(i) for i in items]


@router.post("/waitlist", response_model=WaitlistOut, status_code=201)
async def create_waitlist_entry(
    payload: WaitlistCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("agenda.write")),
    db: AsyncSession = Depends(get_db),
) -> WaitlistOut:
    item = await service.create_waitlist_entry(
        db, clinic_id=clinic_id, data=payload, actor_id=actor.id
    )
    return WaitlistOut.model_validate(item)


@router.post("/waitlist/{item_id}/resolve", response_model=WaitlistOut)
async def resolve_waitlist_entry(
    item_id: uuid.UUID,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("agenda.write")),
    db: AsyncSession = Depends(get_db),
) -> WaitlistOut:
    item = await service.resolve_waitlist_entry(db, clinic_id=clinic_id, item_id=item_id)
    return WaitlistOut.model_validate(item)
