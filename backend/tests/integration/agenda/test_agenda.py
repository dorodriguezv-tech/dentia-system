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
