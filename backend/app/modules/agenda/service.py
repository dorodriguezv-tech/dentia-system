import uuid
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.core.errors import AppError
from app.modules.agenda import rules
from app.modules.agenda.models import (
    Appointment,
    AppointmentStatusHistory,
    Provider,
    ProviderBlock,
    ProviderWorkingHours,
    ReminderTask,
    Resource,
    WaitlistEntry,
)
from app.modules.agenda.schemas import (
    AppointmentCreateRequest,
    BlockCreateRequest,
    ProviderCreateRequest,
    RescheduleRequest,
    ResourceCreateRequest,
    ResourceUpdateRequest,
    StatusChangeRequest,
    WaitlistCreateRequest,
    WorkingHoursCreateRequest,
)
from app.modules.catalogs import service as catalogs_service
from app.modules.encounters import service as encounters_service
from app.modules.encounters.models import Encounter
from app.modules.encounters.schemas import EncounterCreateRequest
from app.modules.iam.models import User
from app.modules.patients.models import Patient


async def _get_patient_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, patient_id: uuid.UUID
) -> Patient:
    patient = await db.get(Patient, patient_id)
    if patient is None or patient.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Paciente no encontrado", status_code=404)
    return patient


async def get_provider_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, provider_id: uuid.UUID
) -> Provider:
    provider = await db.get(Provider, provider_id)
    if provider is None or provider.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Profesional no encontrado", status_code=404)
    return provider


async def get_resource_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, resource_id: uuid.UUID
) -> Resource:
    resource = await db.get(Resource, resource_id)
    if resource is None or resource.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Recurso no encontrado", status_code=404)
    return resource


async def _get_appointment_in_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, appointment_id: uuid.UUID
) -> Appointment:
    appointment = await db.get(Appointment, appointment_id)
    if appointment is None or appointment.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Cita no encontrada", status_code=404)
    return appointment


# --------------------------------------------------------------------------- providers


async def list_providers(db: AsyncSession, *, clinic_id: uuid.UUID) -> list[tuple[Provider, str]]:
    # Fase 12.1 (correccion A1): solo los activos -- al desactivar a un profesional
    # (o quitarle el rol clinico) su Provider se desactiva, no se borra (tiene citas),
    # pero ya no debe ofrecerse para agendar citas nuevas.
    stmt = select(Provider).where(Provider.clinic_id == clinic_id, Provider.is_active.is_(True))
    providers = list((await db.execute(stmt)).scalars().all())
    users = {u.id: u for u in (await db.execute(select(User))).scalars().all()}
    return [(p, users[p.user_id].full_name if p.user_id in users else "") for p in providers]


async def get_provider_for_user(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID
) -> Provider | None:
    stmt = select(Provider).where(Provider.clinic_id == clinic_id, Provider.user_id == user_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def ensure_provider_for_user(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, actor_id: uuid.UUID
) -> Provider:
    """Crea (o reactiva) el Provider de un usuario con rol clinico (A1).

    Idempotente: se llama cada vez que un usuario se crea o se le asigna un rol de
    `rules.PROVIDER_ROLES`, sin que el llamador tenga que saber si ya tenia uno.
    """
    stmt = select(Provider).where(Provider.clinic_id == clinic_id, Provider.user_id == user_id)
    provider = (await db.execute(stmt)).scalar_one_or_none()
    if provider is not None:
        if not provider.is_active:
            provider.is_active = True
        return provider

    existing_providers = (
        (await db.execute(select(Provider).where(Provider.clinic_id == clinic_id))).scalars().all()
    )
    color = rules.next_provider_color(len(existing_providers))

    provider = Provider(clinic_id=clinic_id, user_id=user_id, color=color, created_by=actor_id)
    db.add(provider)
    await db.flush()
    await audit_service.log(
        db,
        action="agenda.provider_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="provider",
        entity_id=str(provider.id),
        details={"user_id": str(user_id), "auto": True},
    )
    return provider


async def set_provider_active_for_user(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, is_active: bool
) -> None:
    """Desactiva (o reactiva) el Provider de un usuario sin borrarlo (A1)."""
    stmt = select(Provider).where(Provider.clinic_id == clinic_id, Provider.user_id == user_id)
    provider = (await db.execute(stmt)).scalar_one_or_none()
    if provider is not None and provider.is_active != is_active:
        provider.is_active = is_active


async def set_provider_default_resource(
    db: AsyncSession, *, clinic_id: uuid.UUID, provider: Provider, resource_id: uuid.UUID | None
) -> None:
    """B2 (Parte B, Fase 12.2): gabinete por defecto de un profesional en esta
    sucursal -- la agenda lo preselecciona al agendar con el (NewAppointmentForm.tsx)."""
    if resource_id is not None:
        await get_resource_in_clinic(db, clinic_id=clinic_id, resource_id=resource_id)
    provider.default_resource_id = resource_id


async def create_provider(
    db: AsyncSession, *, clinic_id: uuid.UUID, data: ProviderCreateRequest, actor_id: uuid.UUID
) -> tuple[Provider, str]:
    user = await db.get(User, data.user_id)
    if user is None:
        raise AppError("NOT_FOUND", "Usuario no encontrado", status_code=404)
    provider = Provider(
        clinic_id=clinic_id, user_id=data.user_id, color=data.color, created_by=actor_id
    )
    db.add(provider)
    await db.flush()
    await set_provider_default_resource(
        db, clinic_id=clinic_id, provider=provider, resource_id=data.default_resource_id
    )
    await audit_service.log(
        db,
        action="agenda.provider_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="provider",
        entity_id=str(provider.id),
        details={"user_id": str(data.user_id)},
    )
    await db.commit()
    return provider, user.full_name


# --------------------------------------------------------------------------- resources


async def list_resources(
    db: AsyncSession, *, clinic_id: uuid.UUID, include_inactive: bool = False
) -> list[Resource]:
    stmt = select(Resource).where(Resource.clinic_id == clinic_id)
    if not include_inactive:
        # Pendiente de B1 (Parte B, Fase 12.2): antes ningun Resource se podia
        # desactivar, asi que esto nunca filtraba nada -- ahora que si se puede
        # (ver update_resource), un gabinete desactivado ya no debe ofrecerse al
        # agendar, igual que un Provider desactivado (A1, Fase 12.1).
        stmt = stmt.where(Resource.is_active.is_(True))
    return list((await db.execute(stmt)).scalars().all())


async def create_resource(
    db: AsyncSession, *, clinic_id: uuid.UUID, data: ResourceCreateRequest, actor_id: uuid.UUID
) -> Resource:
    resource = Resource(clinic_id=clinic_id, name=data.name, created_by=actor_id)
    db.add(resource)
    await db.commit()
    return resource


async def update_resource(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    resource_id: uuid.UUID,
    data: ResourceUpdateRequest,
    actor_id: uuid.UUID,
) -> Resource:
    """Pendiente de B1 (Parte B, Fase 12.2): renombrar o desactivar un gabinete
    desde la pantalla de Catalogos."""
    resource = await get_resource_in_clinic(db, clinic_id=clinic_id, resource_id=resource_id)
    if data.name is not None:
        resource.name = data.name
    if data.is_active is not None:
        resource.is_active = data.is_active
    await audit_service.log(
        db,
        action="agenda.resource_updated",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="resource",
        entity_id=str(resource.id),
    )
    await db.commit()
    return resource


# --------------------------------------------------------------- horarios y bloqueos


async def list_working_hours(
    db: AsyncSession, *, clinic_id: uuid.UUID, provider_id: uuid.UUID
) -> list[ProviderWorkingHours]:
    await get_provider_in_clinic(db, clinic_id=clinic_id, provider_id=provider_id)
    stmt = select(ProviderWorkingHours).where(ProviderWorkingHours.provider_id == provider_id)
    return list((await db.execute(stmt)).scalars().all())


async def create_working_hours(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    provider_id: uuid.UUID,
    data: WorkingHoursCreateRequest,
) -> ProviderWorkingHours:
    await get_provider_in_clinic(db, clinic_id=clinic_id, provider_id=provider_id)
    item = ProviderWorkingHours(
        provider_id=provider_id,
        weekday=data.weekday,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    db.add(item)
    await db.commit()
    return item


async def delete_working_hours(
    db: AsyncSession, *, clinic_id: uuid.UUID, provider_id: uuid.UUID, item_id: uuid.UUID
) -> None:
    await get_provider_in_clinic(db, clinic_id=clinic_id, provider_id=provider_id)
    item = await db.get(ProviderWorkingHours, item_id)
    if item is None or item.provider_id != provider_id:
        raise AppError("NOT_FOUND", "Horario no encontrado", status_code=404)
    await db.delete(item)
    await db.commit()


async def list_blocks(
    db: AsyncSession, *, clinic_id: uuid.UUID, provider_id: uuid.UUID
) -> list[ProviderBlock]:
    await get_provider_in_clinic(db, clinic_id=clinic_id, provider_id=provider_id)
    stmt = select(ProviderBlock).where(ProviderBlock.provider_id == provider_id)
    return list((await db.execute(stmt)).scalars().all())


async def create_block(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    provider_id: uuid.UUID,
    data: BlockCreateRequest,
    actor_id: uuid.UUID,
) -> ProviderBlock:
    await get_provider_in_clinic(db, clinic_id=clinic_id, provider_id=provider_id)
    item = ProviderBlock(
        provider_id=provider_id,
        starts_at=data.starts_at,
        ends_at=data.ends_at,
        reason=data.reason,
        created_by=actor_id,
    )
    db.add(item)
    await db.commit()
    return item


async def delete_block(
    db: AsyncSession, *, clinic_id: uuid.UUID, provider_id: uuid.UUID, item_id: uuid.UUID
) -> None:
    await get_provider_in_clinic(db, clinic_id=clinic_id, provider_id=provider_id)
    item = await db.get(ProviderBlock, item_id)
    if item is None or item.provider_id != provider_id:
        raise AppError("NOT_FOUND", "Bloqueo no encontrado", status_code=404)
    await db.delete(item)
    await db.commit()


# ----------------------------------------------------------------------- disponibilidad


async def _find_conflicts(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    provider_id: uuid.UUID,
    resource_id: uuid.UUID | None,
    starts_at: datetime,
    ends_at: datetime,
    exclude_appointment_id: uuid.UUID | None = None,
) -> list[Appointment]:
    same_provider_or_resource = (
        or_(Appointment.provider_id == provider_id, Appointment.resource_id == resource_id)
        if resource_id is not None
        else (Appointment.provider_id == provider_id)
    )
    stmt = select(Appointment).where(
        Appointment.clinic_id == clinic_id,
        Appointment.status.in_(rules.ACTIVE_STATUSES),
        Appointment.starts_at < ends_at,
        Appointment.ends_at > starts_at,
        same_provider_or_resource,
    )
    if exclude_appointment_id is not None:
        stmt = stmt.where(Appointment.id != exclude_appointment_id)
    return list((await db.execute(stmt)).scalars().all())


async def _warnings_for_slot(
    db: AsyncSession, *, provider_id: uuid.UUID, starts_at: datetime, ends_at: datetime
) -> list[str]:
    """Avisos no bloqueantes: fuera de horario laboral o dentro de un bloqueo. El
    horario laboral/bloqueos son informativos (ver pendiente en docs/PENDIENTES_CLINICOS.md),
    a diferencia del traslape de citas, que si se rechaza."""
    warnings: list[str] = []

    hours_stmt = select(ProviderWorkingHours).where(
        ProviderWorkingHours.provider_id == provider_id,
        ProviderWorkingHours.weekday == starts_at.weekday(),
    )
    working_hours = list((await db.execute(hours_stmt)).scalars().all())
    if working_hours:
        start_t, end_t = starts_at.time(), ends_at.time()
        within = any(wh.start_time <= start_t and end_t <= wh.end_time for wh in working_hours)
        if not within:
            warnings.append("La cita queda fuera del horario laboral del profesional.")
    blocks_stmt = select(ProviderBlock).where(
        ProviderBlock.provider_id == provider_id,
        ProviderBlock.starts_at < ends_at,
        ProviderBlock.ends_at > starts_at,
    )
    if (await db.execute(blocks_stmt)).scalars().first() is not None:
        warnings.append(
            "La cita coincide con un bloqueo (vacaciones, permiso, etc.) del profesional."
        )
    return warnings


_FREE_SLOT_STEP_MINUTES = 15


async def find_free_slots(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    provider_id: uuid.UUID,
    day: date,
    duration_minutes: int,
    limit: int = 3,
) -> list[time]:
    """Huecos libres reales de un profesional en un dia (Fase 13, 13.4, sec. 4.5
    del diseno: Dentia propone horarios reales en vez de solo pedir la hora).
    Candidatos cada 15 minutos dentro de cada ventana de horario laboral de ese
    dia de la semana, descartando lo que choque con un bloqueo o una cita activa
    -- las mismas reglas de `create_appointment`, solo explorando en vez de
    reservar. Sin horario laboral ese dia, no hay huecos que proponer (es
    informativo igual que `_warnings_for_slot`, pero aqui no hay nada que
    inventar)."""
    provider = await get_provider_in_clinic(db, clinic_id=clinic_id, provider_id=provider_id)
    hours_stmt = select(ProviderWorkingHours).where(
        ProviderWorkingHours.provider_id == provider_id,
        ProviderWorkingHours.weekday == day.weekday(),
    )
    working_hours = list((await db.execute(hours_stmt)).scalars().all())
    if not working_hours:
        return []

    day_start = datetime.combine(day, time.min, tzinfo=UTC)
    day_end = datetime.combine(day, time.max, tzinfo=UTC)
    busy_appointments = await _find_conflicts(
        db,
        clinic_id=clinic_id,
        provider_id=provider_id,
        resource_id=provider.default_resource_id,
        starts_at=day_start,
        ends_at=day_end,
    )
    blocks_stmt = select(ProviderBlock).where(
        ProviderBlock.provider_id == provider_id,
        ProviderBlock.starts_at < day_end,
        ProviderBlock.ends_at > day_start,
    )
    blocks = list((await db.execute(blocks_stmt)).scalars().all())
    busy_ranges = [(a.starts_at, a.ends_at) for a in busy_appointments] + [
        (b.starts_at, b.ends_at) for b in blocks
    ]

    now = datetime.now(UTC)
    step = timedelta(minutes=_FREE_SLOT_STEP_MINUTES)
    duration = timedelta(minutes=duration_minutes)
    slots: list[time] = []
    for working_hour in sorted(working_hours, key=lambda wh: wh.start_time):
        candidate = datetime.combine(day, working_hour.start_time, tzinfo=UTC)
        window_end = datetime.combine(day, working_hour.end_time, tzinfo=UTC)
        while candidate + duration <= window_end:
            free = candidate >= now and not any(
                candidate < busy_end and candidate + duration > busy_start
                for busy_start, busy_end in busy_ranges
            )
            if free:
                slots.append(candidate.time())
                if len(slots) >= limit:
                    return slots
            candidate += step
    return slots


_HOURLY_STEP_MINUTES = 60


async def get_day_schedule(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    provider_id: uuid.UUID,
    day: date,
    duration_minutes: int,
) -> list[tuple[time, bool]]:
    """Cuadricula de horas completas (9:00, 10:00, ...) del horario laboral de ese
    dia, cada una marcada disponible u ocupada. Reporte al probar en un telefono
    real: `find_free_slots` solo devuelve unos pocos huecos dispersos en pasos de
    15 minutos (medias y cuartos); aqui, en cambio, se recorre cada hora completa
    para elegir tocando en vez de escribir la hora, con las mismas reglas de
    conflicto que `create_appointment`."""
    provider = await get_provider_in_clinic(db, clinic_id=clinic_id, provider_id=provider_id)
    hours_stmt = select(ProviderWorkingHours).where(
        ProviderWorkingHours.provider_id == provider_id,
        ProviderWorkingHours.weekday == day.weekday(),
    )
    working_hours = list((await db.execute(hours_stmt)).scalars().all())
    if not working_hours:
        return []

    day_start = datetime.combine(day, time.min, tzinfo=UTC)
    day_end = datetime.combine(day, time.max, tzinfo=UTC)
    busy_appointments = await _find_conflicts(
        db,
        clinic_id=clinic_id,
        provider_id=provider_id,
        resource_id=provider.default_resource_id,
        starts_at=day_start,
        ends_at=day_end,
    )
    blocks_stmt = select(ProviderBlock).where(
        ProviderBlock.provider_id == provider_id,
        ProviderBlock.starts_at < day_end,
        ProviderBlock.ends_at > day_start,
    )
    blocks = list((await db.execute(blocks_stmt)).scalars().all())
    busy_ranges = [(a.starts_at, a.ends_at) for a in busy_appointments] + [
        (b.starts_at, b.ends_at) for b in blocks
    ]

    now = datetime.now(UTC)
    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=_HOURLY_STEP_MINUTES)
    results: list[tuple[time, bool]] = []
    seen: set[time] = set()
    for working_hour in sorted(working_hours, key=lambda wh: wh.start_time):
        window_start = datetime.combine(day, working_hour.start_time, tzinfo=UTC)
        window_end = datetime.combine(day, working_hour.end_time, tzinfo=UTC)
        candidate = window_start.replace(minute=0, second=0, microsecond=0)
        if candidate < window_start:
            candidate += step
        while candidate < window_end:
            if candidate.time() not in seen:
                seen.add(candidate.time())
                available = (
                    candidate >= now
                    and candidate + duration <= window_end
                    and not any(
                        candidate < busy_end and candidate + duration > busy_start
                        for busy_start, busy_end in busy_ranges
                    )
                )
                results.append((candidate.time(), available))
            candidate += step
    return sorted(results, key=lambda r: r[0])


def _conflict_error(conflicts: list[Appointment]) -> AppError:
    return AppError(
        "APPOINTMENT_CONFLICT",
        "El profesional o el recurso ya tienen una cita en ese horario",
        details={"conflicting_appointment_ids": [str(c.id) for c in conflicts]},
        status_code=409,
    )


async def _validate_appointment_type(
    db: AsyncSession, *, clinic_id: uuid.UUID, appointment_type: str
) -> int:
    """B1 (Parte B, Fase 12.2): "Tipos de consulta/cita" ya no es un diccionario fijo
    en codigo (ver agenda/rules.py) -- valida contra el catalogo administrable de la
    sucursal y falla claro si el codigo no existe o esta desactivado, en vez de
    guardar cualquier texto sin verificar. Regresa la duracion por defecto (para
    cuando la peticion no trae `ends_at` explicito)."""
    items = await catalogs_service.list_items(
        db, clinic_id=clinic_id, catalog_type="appointment_type"
    )
    item = next((i for i in items if i.code == appointment_type), None)
    if item is None:
        raise AppError(
            "INVALID_APPOINTMENT_TYPE",
            "El tipo de cita no existe o esta desactivado en esta sucursal",
            status_code=400,
        )
    minutes = item.extra.get("default_minutes")
    return minutes if isinstance(minutes, int) else rules.DEFAULT_APPOINTMENT_DURATION_MINUTES


# ------------------------------------------------------------------------- citas


async def create_appointment(
    db: AsyncSession, *, clinic_id: uuid.UUID, data: AppointmentCreateRequest, actor_id: uuid.UUID
) -> tuple[Appointment, list[str]]:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=data.patient_id)
    await get_provider_in_clinic(db, clinic_id=clinic_id, provider_id=data.provider_id)
    if data.resource_id is not None:
        await get_resource_in_clinic(db, clinic_id=clinic_id, resource_id=data.resource_id)

    default_minutes = await _validate_appointment_type(
        db, clinic_id=clinic_id, appointment_type=data.appointment_type
    )
    ends_at = data.ends_at or (data.starts_at + timedelta(minutes=default_minutes))
    if ends_at <= data.starts_at:
        raise AppError(
            "INVALID_RANGE", "La hora de termino debe ser posterior al inicio", status_code=422
        )

    conflicts = await _find_conflicts(
        db,
        clinic_id=clinic_id,
        provider_id=data.provider_id,
        resource_id=data.resource_id,
        starts_at=data.starts_at,
        ends_at=ends_at,
    )
    if conflicts:
        raise _conflict_error(conflicts)

    warnings = await _warnings_for_slot(
        db, provider_id=data.provider_id, starts_at=data.starts_at, ends_at=ends_at
    )

    appointment = Appointment(
        clinic_id=clinic_id,
        patient_id=data.patient_id,
        provider_id=data.provider_id,
        resource_id=data.resource_id,
        appointment_type=data.appointment_type,
        starts_at=data.starts_at,
        ends_at=ends_at,
        status="RESERVADA",
        notes=data.notes,
        created_by=actor_id,
    )
    db.add(appointment)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict_error([]) from exc

    db.add(
        AppointmentStatusHistory(
            appointment_id=appointment.id,
            from_status=None,
            to_status="RESERVADA",
            changed_by=actor_id,
            changed_at=datetime.now(UTC),
        )
    )
    db.add(
        ReminderTask(
            appointment_id=appointment.id,
            kind="24h_antes",
            scheduled_for=data.starts_at - timedelta(hours=24),
            status="PENDING",
        )
    )
    await audit_service.log(
        db,
        action="agenda.appointment_created",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="appointment",
        entity_id=str(appointment.id),
        details={"patient_id": str(data.patient_id), "provider_id": str(data.provider_id)},
    )
    await db.commit()
    return appointment, warnings


async def list_appointments(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    starts_from: datetime,
    starts_to: datetime,
    provider_id: uuid.UUID | None = None,
    resource_id: uuid.UUID | None = None,
    patient_id: uuid.UUID | None = None,
) -> list[dict[str, object]]:
    stmt = select(Appointment).where(
        Appointment.clinic_id == clinic_id,
        Appointment.starts_at < starts_to,
        Appointment.ends_at > starts_from,
    )
    if provider_id is not None:
        stmt = stmt.where(Appointment.provider_id == provider_id)
    if resource_id is not None:
        stmt = stmt.where(Appointment.resource_id == resource_id)
    if patient_id is not None:
        stmt = stmt.where(Appointment.patient_id == patient_id)
    stmt = stmt.order_by(Appointment.starts_at)
    appointments = list((await db.execute(stmt)).scalars().all())

    patients = {p.id: p for p in (await db.execute(select(Patient))).scalars().all()}
    providers = {p.id: p for p in (await db.execute(select(Provider))).scalars().all()}
    users = {u.id: u for u in (await db.execute(select(User))).scalars().all()}
    resources = {r.id: r for r in (await db.execute(select(Resource))).scalars().all()}

    items = []
    for appointment in appointments:
        provider = providers.get(appointment.provider_id)
        provider_user = users.get(provider.user_id) if provider else None
        patient = patients.get(appointment.patient_id)
        resource = resources.get(appointment.resource_id) if appointment.resource_id else None
        items.append(
            {
                "id": appointment.id,
                "patient_id": appointment.patient_id,
                "patient_full_name": patient.full_name if patient else "",
                "provider_id": appointment.provider_id,
                "provider_full_name": provider_user.full_name if provider_user else "",
                "provider_color": provider.color if provider else "#2BB3A3",
                "resource_id": appointment.resource_id,
                "resource_name": resource.name if resource else None,
                "appointment_type": appointment.appointment_type,
                "starts_at": appointment.starts_at,
                "ends_at": appointment.ends_at,
                "status": appointment.status,
                "notes": appointment.notes,
            }
        )
    return items


async def change_status(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    appointment_id: uuid.UUID,
    data: StatusChangeRequest,
    actor_id: uuid.UUID,
) -> Appointment:
    appointment = await _get_appointment_in_clinic(
        db, clinic_id=clinic_id, appointment_id=appointment_id
    )
    if not rules.can_transition(appointment.status, data.status):
        raise AppError(
            "INVALID_TRANSITION",
            f"No se puede pasar de {appointment.status} a {data.status}",
            status_code=409,
        )
    if data.status in rules.REASON_REQUIRED_STATUSES and not data.reason:
        raise AppError(
            "REASON_REQUIRED", f"El estado {data.status} exige un motivo", status_code=422
        )

    from_status = appointment.status
    appointment.status = data.status
    if data.status == "CANCELADA":
        appointment.cancel_reason = data.reason

    db.add(
        AppointmentStatusHistory(
            appointment_id=appointment.id,
            from_status=from_status,
            to_status=data.status,
            reason=data.reason,
            changed_by=actor_id,
            changed_at=datetime.now(UTC),
        )
    )
    await audit_service.log(
        db,
        action="agenda.appointment_status_changed",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="appointment",
        entity_id=str(appointment.id),
        details={"from": from_status, "to": data.status, "reason": data.reason},
    )
    await db.commit()
    return appointment


async def reschedule_appointment(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    appointment_id: uuid.UUID,
    data: RescheduleRequest,
    actor_id: uuid.UUID,
) -> tuple[Appointment, list[str]]:
    old = await _get_appointment_in_clinic(db, clinic_id=clinic_id, appointment_id=appointment_id)
    if not rules.is_editable(old.status):
        raise AppError(
            "INVALID_TRANSITION",
            f"No se puede reprogramar una cita en estado {old.status}",
            status_code=409,
        )

    new_provider_id = data.provider_id or old.provider_id
    new_resource_id = data.resource_id if data.resource_id is not None else old.resource_id
    duration = old.ends_at - old.starts_at
    new_ends_at = data.ends_at or (data.starts_at + duration)
    if new_ends_at <= data.starts_at:
        raise AppError(
            "INVALID_RANGE", "La hora de termino debe ser posterior al inicio", status_code=422
        )

    if new_provider_id != old.provider_id:
        await get_provider_in_clinic(db, clinic_id=clinic_id, provider_id=new_provider_id)
    if new_resource_id is not None and new_resource_id != old.resource_id:
        await get_resource_in_clinic(db, clinic_id=clinic_id, resource_id=new_resource_id)

    conflicts = await _find_conflicts(
        db,
        clinic_id=clinic_id,
        provider_id=new_provider_id,
        resource_id=new_resource_id,
        starts_at=data.starts_at,
        ends_at=new_ends_at,
        exclude_appointment_id=old.id,
    )
    if conflicts:
        raise _conflict_error(conflicts)

    warnings = await _warnings_for_slot(
        db, provider_id=new_provider_id, starts_at=data.starts_at, ends_at=new_ends_at
    )

    from_status = old.status
    old.status = "REPROGRAMADA"
    db.add(
        AppointmentStatusHistory(
            appointment_id=old.id,
            from_status=from_status,
            to_status="REPROGRAMADA",
            reason=data.reason or "Reprogramada",
            changed_by=actor_id,
            changed_at=datetime.now(UTC),
        )
    )

    new_appointment = Appointment(
        clinic_id=clinic_id,
        patient_id=old.patient_id,
        provider_id=new_provider_id,
        resource_id=new_resource_id,
        appointment_type=old.appointment_type,
        starts_at=data.starts_at,
        ends_at=new_ends_at,
        status="RESERVADA",
        notes=old.notes,
        rescheduled_from_id=old.id,
        created_by=actor_id,
    )
    db.add(new_appointment)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict_error([]) from exc

    db.add(
        AppointmentStatusHistory(
            appointment_id=new_appointment.id,
            from_status=None,
            to_status="RESERVADA",
            changed_by=actor_id,
            changed_at=datetime.now(UTC),
        )
    )
    db.add(
        ReminderTask(
            appointment_id=new_appointment.id,
            kind="24h_antes",
            scheduled_for=data.starts_at - timedelta(hours=24),
            status="PENDING",
        )
    )
    await audit_service.log(
        db,
        action="agenda.appointment_rescheduled",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="appointment",
        entity_id=str(old.id),
        details={"new_appointment_id": str(new_appointment.id)},
    )
    await db.commit()
    return new_appointment, warnings


async def start_encounter_from_appointment(
    db: AsyncSession, *, clinic_id: uuid.UUID, appointment_id: uuid.UUID, actor_id: uuid.UUID
) -> Encounter:
    appointment = await _get_appointment_in_clinic(
        db, clinic_id=clinic_id, appointment_id=appointment_id
    )
    if not rules.can_transition(appointment.status, "EN_ATENCION"):
        raise AppError(
            "INVALID_TRANSITION",
            f"No se puede iniciar la atencion desde el estado {appointment.status}",
            status_code=409,
        )
    provider = await get_provider_in_clinic(
        db, clinic_id=clinic_id, provider_id=appointment.provider_id
    )

    from_status = appointment.status
    appointment.status = "EN_ATENCION"
    db.add(
        AppointmentStatusHistory(
            appointment_id=appointment.id,
            from_status=from_status,
            to_status="EN_ATENCION",
            changed_by=actor_id,
            changed_at=datetime.now(UTC),
        )
    )
    await audit_service.log(
        db,
        action="agenda.appointment_status_changed",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="appointment",
        entity_id=str(appointment.id),
        details={"from": from_status, "to": "EN_ATENCION"},
    )
    await db.commit()

    return await encounters_service.create_encounter(
        db,
        clinic_id=clinic_id,
        data=EncounterCreateRequest(
            patient_id=appointment.patient_id, appointment_id=appointment.id
        ),
        professional_id=provider.user_id,
    )


async def list_reminder_tasks(
    db: AsyncSession, *, clinic_id: uuid.UUID, appointment_id: uuid.UUID
) -> list[ReminderTask]:
    await _get_appointment_in_clinic(db, clinic_id=clinic_id, appointment_id=appointment_id)
    stmt = select(ReminderTask).where(ReminderTask.appointment_id == appointment_id)
    return list((await db.execute(stmt)).scalars().all())


# --------------------------------------------------------------------- lista de espera


async def list_waitlist(db: AsyncSession, *, clinic_id: uuid.UUID) -> list[WaitlistEntry]:
    stmt = (
        select(WaitlistEntry)
        .where(WaitlistEntry.clinic_id == clinic_id, WaitlistEntry.resolved.is_(False))
        .order_by(WaitlistEntry.created_at)
    )
    return list((await db.execute(stmt)).scalars().all())


async def create_waitlist_entry(
    db: AsyncSession, *, clinic_id: uuid.UUID, data: WaitlistCreateRequest, actor_id: uuid.UUID
) -> WaitlistEntry:
    await _get_patient_in_clinic(db, clinic_id=clinic_id, patient_id=data.patient_id)
    if data.provider_id is not None:
        await get_provider_in_clinic(db, clinic_id=clinic_id, provider_id=data.provider_id)
    item = WaitlistEntry(
        clinic_id=clinic_id,
        patient_id=data.patient_id,
        provider_id=data.provider_id,
        notes=data.notes,
        created_by=actor_id,
    )
    db.add(item)
    await db.commit()
    return item


async def resolve_waitlist_entry(
    db: AsyncSession, *, clinic_id: uuid.UUID, item_id: uuid.UUID
) -> WaitlistEntry:
    item = await db.get(WaitlistEntry, item_id)
    if item is None or item.clinic_id != clinic_id:
        raise AppError("NOT_FOUND", "Registro de lista de espera no encontrado", status_code=404)
    item.resolved = True
    item.resolved_at = datetime.now(UTC)
    await db.commit()
    return item
