from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agenda.models import Appointment
from app.modules.patients.schemas import PatientCreateRequest
from app.modules.patients.service import create_patient


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _headers(token: str, clinic_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic_id)}


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def _make_patient(db_session: AsyncSession, clinic, actor_id) -> str:
    patient = await create_patient(
        db_session,
        clinic_id=clinic.id,
        data=PatientCreateRequest(
            first_name="Jose", last_name_paternal="Perez", date_of_birth="1990-05-20"
        ),
        actor_id=actor_id,
    )
    return str(patient.id)


async def _setup(client: AsyncClient, make_user, clinic, db_session: AsyncSession):
    """Admin crea el provider; retorna (admin_headers, provider_id, patient_id, odonto_user)."""
    admin = await make_user(email="admin@example.com", role_code="admin_clinica")
    admin_token = await _login(client, "admin@example.com")
    admin_headers = _headers(admin_token, clinic.id)

    odonto = await make_user(email="odonto@example.com", role_code="odontologo")
    provider_resp = await client.post(
        "/api/v1/providers", headers=admin_headers, json={"user_id": str(odonto.id)}
    )
    assert provider_resp.status_code == 201, provider_resp.text
    provider_id = provider_resp.json()["id"]

    patient_id = await _make_patient(db_session, clinic, admin.id)
    return admin_headers, provider_id, patient_id, odonto


MONDAY_9AM = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


async def test_create_provider_and_resource(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    admin_headers, provider_id, _patient_id, odonto = await _setup(
        client, make_user, clinic, db_session
    )
    assert provider_id

    resource_resp = await client.post(
        "/api/v1/resources", headers=admin_headers, json={"name": "Gabinete 1"}
    )
    assert resource_resp.status_code == 201
    assert resource_resp.json()["name"] == "Gabinete 1"


async def test_rename_and_deactivate_resource(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """Pendiente de B1 (Parte B, Fase 12.2): administrar Gabinetes desde Catalogos."""
    admin_headers, _provider_id, _patient_id, _odonto = await _setup(
        client, make_user, clinic, db_session
    )
    resource_resp = await client.post(
        "/api/v1/resources", headers=admin_headers, json={"name": "Gabinete viejo"}
    )
    resource_id = resource_resp.json()["id"]

    rename_resp = await client.patch(
        f"/api/v1/resources/{resource_id}", headers=admin_headers, json={"name": "Gabinete 2"}
    )
    assert rename_resp.status_code == 200
    assert rename_resp.json()["name"] == "Gabinete 2"

    deactivate_resp = await client.patch(
        f"/api/v1/resources/{resource_id}", headers=admin_headers, json={"is_active": False}
    )
    assert deactivate_resp.status_code == 200
    assert deactivate_resp.json()["is_active"] is False

    default_listing = await client.get("/api/v1/resources", headers=admin_headers)
    assert resource_id not in [r["id"] for r in default_listing.json()]

    with_inactive = await client.get(
        "/api/v1/resources", params={"include_inactive": "true"}, headers=admin_headers
    )
    assert resource_id in [r["id"] for r in with_inactive.json()]


async def test_a_role_without_agenda_write_requesting_inactive_resources_only_sees_active_ones(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """`asistente` tiene agenda.read pero no agenda.write (ve la agenda, no la
    administra) -- igual que un rol sin `catalogs.manage` con los catalogos."""
    admin_headers, _provider_id, _patient_id, _odonto = await _setup(
        client, make_user, clinic, db_session
    )
    resource_resp = await client.post(
        "/api/v1/resources", headers=admin_headers, json={"name": "Gabinete 3"}
    )
    resource_id = resource_resp.json()["id"]
    await client.patch(
        f"/api/v1/resources/{resource_id}", headers=admin_headers, json={"is_active": False}
    )

    await make_user(email="asistente@example.com", role_code="asistente")
    asistente_token = await _login(client, "asistente@example.com")
    asistente_headers = _headers(asistente_token, clinic.id)
    response = await client.get(
        "/api/v1/resources", params={"include_inactive": "true"}, headers=asistente_headers
    )

    assert response.status_code == 200
    assert resource_id not in [r["id"] for r in response.json()]


async def test_create_provider_with_a_default_resource(
    client: AsyncClient, make_user, clinic
) -> None:
    """B2 (Parte B, Fase 12.2): la agenda preselecciona este gabinete al agendar
    con el profesional (ver NewAppointmentForm.tsx)."""
    await make_user(email="admin@example.com", role_code="admin_clinica")
    headers = _headers(await _login(client, "admin@example.com"), clinic.id)
    odonto = await make_user(email="odonto2@example.com", role_code="odontologo")

    resource_resp = await client.post(
        "/api/v1/resources", headers=headers, json={"name": "Gabinete 2"}
    )
    resource_id = resource_resp.json()["id"]

    provider_resp = await client.post(
        "/api/v1/providers",
        headers=headers,
        json={"user_id": str(odonto.id), "default_resource_id": resource_id},
    )
    assert provider_resp.status_code == 201, provider_resp.text
    assert provider_resp.json()["default_resource_id"] == resource_id

    listed = await client.get("/api/v1/providers", headers=headers)
    by_id = {p["id"]: p for p in listed.json()}
    assert by_id[provider_resp.json()["id"]]["default_resource_id"] == resource_id


async def test_create_provider_rejects_a_default_resource_from_another_clinic(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    from sqlalchemy import select

    from app.modules.iam.models import Clinic, Role, UserClinic

    other_clinic = Clinic(organization_id=clinic.organization_id, name="Otra sucursal")
    db_session.add(other_clinic)
    await db_session.flush()

    admin = await make_user(email="admin@example.com", role_code="admin_clinica")
    admin_role = (
        await db_session.execute(select(Role).where(Role.code == "admin_clinica"))
    ).scalar_one()
    db_session.add(UserClinic(user_id=admin.id, clinic_id=other_clinic.id, role_id=admin_role.id))
    await db_session.commit()

    headers = _headers(await _login(client, "admin@example.com"), clinic.id)
    odonto = await make_user(email="odonto3@example.com", role_code="odontologo")

    other_headers = _headers(await _login(client, "admin@example.com"), other_clinic.id)
    foreign_resource_resp = await client.post(
        "/api/v1/resources", headers=other_headers, json={"name": "Gabinete ajeno"}
    )
    foreign_resource_id = foreign_resource_resp.json()["id"]

    response = await client.post(
        "/api/v1/providers",
        headers=headers,
        json={"user_id": str(odonto.id), "default_resource_id": foreign_resource_id},
    )
    assert response.status_code == 404


async def test_create_appointment_computes_default_duration(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, provider_id, patient_id, _odonto = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": _iso(MONDAY_9AM),
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "RESERVADA"
    assert _parse(body["ends_at"]) == MONDAY_9AM + timedelta(minutes=30)


async def test_create_appointment_rejects_a_type_not_in_the_clinic_catalog(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """B1 (Parte B, Fase 12.2): 'Tipos de consulta/cita' ya no es un Literal fijo,
    sino el catalogo administrable de la sucursal -- un codigo que no esta ahi (o
    que un administrador desactivo) se rechaza desde el service, no desde Pydantic."""
    headers, provider_id, patient_id, _odonto = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "no_existe",
            "starts_at": _iso(MONDAY_9AM),
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_APPOINTMENT_TYPE"


async def test_a_new_appointment_type_from_the_catalog_works_immediately_when_scheduling(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """Criterio de aceptacion de B1: 'el administrador crea el tipo de consulta
    Valoracion ortodoncia - 45 min y aparece de inmediato al agendar'."""
    headers, provider_id, patient_id, _odonto = await _setup(client, make_user, clinic, db_session)

    create_type_response = await client.post(
        "/api/v1/catalogs/appointment_type",
        headers=headers,
        json={
            "code": "valoracion_ortodoncia",
            "name": "Valoracion ortodoncia",
            "extra": {"default_minutes": 45},
        },
    )
    assert create_type_response.status_code == 201, create_type_response.text

    response = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "valoracion_ortodoncia",
            "starts_at": _iso(MONDAY_9AM),
        },
    )

    assert response.status_code == 201, response.text
    assert _parse(response.json()["ends_at"]) == MONDAY_9AM + timedelta(minutes=45)


async def test_create_appointment_rejects_invalid_range(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, provider_id, patient_id, _odonto = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": _iso(MONDAY_9AM),
            "ends_at": _iso(MONDAY_9AM - timedelta(minutes=10)),
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_RANGE"


async def test_create_appointment_rejects_overlap_same_provider(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """Prueba obligatoria (CLAUDE.md Fase 6): el backend valida traslapes."""
    headers, provider_id, patient_id, _odonto = await _setup(client, make_user, clinic, db_session)

    first = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": _iso(MONDAY_9AM),
        },
    )
    assert first.status_code == 201

    overlapping = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": _iso(MONDAY_9AM + timedelta(minutes=15)),
        },
    )
    assert overlapping.status_code == 409
    assert overlapping.json()["code"] == "APPOINTMENT_CONFLICT"

    back_to_back = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": _iso(MONDAY_9AM + timedelta(minutes=30)),
        },
    )
    assert back_to_back.status_code == 201


async def test_status_transition_requires_reason_to_cancel(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, provider_id, patient_id, _odonto = await _setup(client, make_user, clinic, db_session)
    created = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": _iso(MONDAY_9AM),
        },
    )
    appointment_id = created.json()["id"]

    without_reason = await client.patch(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"status": "CANCELADA"},
    )
    assert without_reason.status_code == 422
    assert without_reason.json()["code"] == "REASON_REQUIRED"

    with_reason = await client.patch(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"status": "CANCELADA", "reason": "El paciente llamo a cancelar"},
    )
    assert with_reason.status_code == 200
    assert with_reason.json()["status"] == "CANCELADA"


async def test_invalid_status_transition_is_rejected(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, provider_id, patient_id, _odonto = await _setup(client, make_user, clinic, db_session)
    created = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": _iso(MONDAY_9AM),
        },
    )
    appointment_id = created.json()["id"]

    await client.patch(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"status": "EN_ATENCION"},
    )
    terminada = await client.patch(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"status": "TERMINADA"},
    )
    assert terminada.status_code == 200

    invalid = await client.patch(
        f"/api/v1/appointments/{appointment_id}/status",
        headers=headers,
        json={"status": "CONFIRMADA"},
    )
    assert invalid.status_code == 409
    assert invalid.json()["code"] == "INVALID_TRANSITION"


async def test_reschedule_creates_new_appointment_and_marks_old_reprogramada(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, provider_id, patient_id, _odonto = await _setup(client, make_user, clinic, db_session)
    created = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": _iso(MONDAY_9AM),
        },
    )
    old_id = created.json()["id"]
    new_start = MONDAY_9AM + timedelta(days=1)

    rescheduled = await client.post(
        f"/api/v1/appointments/{old_id}/reschedule",
        headers=headers,
        json={"starts_at": _iso(new_start), "reason": "El paciente pidio otro dia"},
    )
    assert rescheduled.status_code == 200, rescheduled.text
    new_body = rescheduled.json()
    assert new_body["id"] != old_id
    assert new_body["rescheduled_from_id"] == old_id
    assert new_body["status"] == "RESERVADA"
    assert _parse(new_body["starts_at"]) == new_start

    old_status = await db_session.get(Appointment, old_id)
    assert old_status.status == "REPROGRAMADA"

    # El horario viejo queda libre: una cita nueva ahi mismo ya no choca con la vieja.
    reuse_old_slot = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": _iso(MONDAY_9AM),
        },
    )
    assert reuse_old_slot.status_code == 201


async def test_reschedule_rejects_conflicting_new_slot(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, provider_id, patient_id, _odonto = await _setup(client, make_user, clinic, db_session)
    first = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": _iso(MONDAY_9AM),
        },
    )
    second_start = MONDAY_9AM + timedelta(hours=2)
    second = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": _iso(second_start),
        },
    )
    assert second.status_code == 201

    reschedule_into_second = await client.post(
        f"/api/v1/appointments/{first.json()['id']}/reschedule",
        headers=headers,
        json={"starts_at": _iso(second_start)},
    )
    assert reschedule_into_second.status_code == 409
    assert reschedule_into_second.json()["code"] == "APPOINTMENT_CONFLICT"


async def test_start_encounter_creates_encounter_and_requires_records_write(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, provider_id, patient_id, odonto = await _setup(client, make_user, clinic, db_session)
    created = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": _iso(MONDAY_9AM),
        },
    )
    appointment_id = created.json()["id"]

    # recepcion tiene agenda.write pero no records.write: no puede iniciar la atencion.
    await make_user(email="recepcion@example.com", role_code="recepcion")
    recepcion_token = await _login(client, "recepcion@example.com")
    denied = await client.post(
        f"/api/v1/appointments/{appointment_id}/start-encounter",
        headers=_headers(recepcion_token, clinic.id),
    )
    assert denied.status_code == 403

    odonto_token = await _login(client, "odonto@example.com")
    started = await client.post(
        f"/api/v1/appointments/{appointment_id}/start-encounter",
        headers=_headers(odonto_token, clinic.id),
    )
    assert started.status_code == 200, started.text
    assert started.json()["appointment_id"] == appointment_id
    assert started.json()["professional_id"] == str(odonto.id)

    appointment_after = await db_session.get(Appointment, appointment_id)
    assert appointment_after.status == "EN_ATENCION"


async def test_reminder_task_registered_on_create(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, provider_id, patient_id, _odonto = await _setup(client, make_user, clinic, db_session)
    created = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": _iso(MONDAY_9AM),
        },
    )
    appointment_id = created.json()["id"]

    reminders = await client.get(
        f"/api/v1/appointments/{appointment_id}/reminders", headers=headers
    )
    assert reminders.status_code == 200
    body = reminders.json()
    assert len(body) == 1
    assert body[0]["kind"] == "24h_antes"
    assert _parse(body[0]["scheduled_for"]) == MONDAY_9AM - timedelta(hours=24)


async def test_waitlist_create_and_resolve(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, _provider_id, patient_id, _odonto = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        "/api/v1/waitlist", headers=headers, json={"patient_id": patient_id, "notes": "Urgente"}
    )
    assert created.status_code == 201
    assert created.json()["resolved"] is False

    listed = await client.get("/api/v1/waitlist", headers=headers)
    assert len(listed.json()) == 1

    resolved = await client.post(
        f"/api/v1/waitlist/{created.json()['id']}/resolve", headers=headers
    )
    assert resolved.status_code == 200
    assert resolved.json()["resolved"] is True

    listed_after = await client.get("/api/v1/waitlist", headers=headers)
    assert listed_after.json() == []


async def test_exclude_constraint_is_a_backup_against_overlap(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """Prueba obligatoria (CLAUDE.md Fase 6): la restriccion EXCLUDE de Postgres
    (btree_gist + tstzrange) rechaza el traslape incluso si se evita la validacion de
    la capa de aplicacion insertando directamente por el ORM."""
    headers, provider_id, patient_id, _odonto = await _setup(client, make_user, clinic, db_session)

    db_session.add(
        Appointment(
            clinic_id=clinic.id,
            patient_id=patient_id,
            provider_id=provider_id,
            appointment_type="consulta",
            starts_at=MONDAY_9AM,
            ends_at=MONDAY_9AM + timedelta(minutes=30),
            status="RESERVADA",
        )
    )
    await db_session.commit()

    db_session.add(
        Appointment(
            clinic_id=clinic.id,
            patient_id=patient_id,
            provider_id=provider_id,
            appointment_type="consulta",
            starts_at=MONDAY_9AM + timedelta(minutes=10),
            ends_at=MONDAY_9AM + timedelta(minutes=40),
            status="RESERVADA",
        )
    )
    with pytest.raises(IntegrityError, match="ux_appointments_no_overlap_provider"):
        await db_session.commit()
    await db_session.rollback()


async def test_list_appointments_accepts_range_and_includes_full_names(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """B3 (docs/05_APP_MOVIL.md Sec. 7): la app movil pinta la agenda sin una
    peticion por cita. El contrato ya existe tal cual lo necesita (query
    `starts_from`/`starts_to`, `patient_full_name`/`provider_full_name` en cada
    cita): esta prueba lo fija para que no se rompa sin darse cuenta."""
    headers, provider_id, patient_id, odonto = await _setup(client, make_user, clinic, db_session)
    await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": _iso(MONDAY_9AM),
        },
    )

    response = await client.get(
        "/api/v1/appointments",
        headers=headers,
        params={
            "starts_from": _iso(MONDAY_9AM - timedelta(hours=1)),
            "starts_to": _iso(MONDAY_9AM + timedelta(hours=1)),
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 1
    assert body[0]["patient_full_name"] == "Jose Perez"
    assert body[0]["provider_full_name"] == odonto.full_name
