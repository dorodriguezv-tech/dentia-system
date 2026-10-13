from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patients.schemas import PatientCreateRequest
from app.modules.patients.service import create_patient


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _headers(token: str, clinic_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic_id)}


async def _setup(client: AsyncClient, make_user, clinic, db_session: AsyncSession):
    """B8 (docs/06_APP_MOVIL_V1_1_PARIDAD.md sec. 4): mismo patron que
    tests/integration/agenda/test_agenda.py::_setup."""
    admin = await make_user(email="admin@example.com", role_code="admin_clinica")
    admin_token = await _login(client, "admin@example.com")
    admin_headers = _headers(admin_token, clinic.id)

    odonto = await make_user(email="odonto@example.com", role_code="odontologo")
    provider_resp = await client.post(
        "/api/v1/providers", headers=admin_headers, json={"user_id": str(odonto.id)}
    )
    provider_id = provider_resp.json()["id"]

    patient = await create_patient(
        db_session,
        clinic_id=clinic.id,
        data=PatientCreateRequest(
            first_name="Jose", last_name_paternal="Perez", date_of_birth="1990-05-20"
        ),
        actor_id=admin.id,
    )
    return admin_headers, provider_id, str(patient.id)


# 2026-11-02 es lunes; 2026-11-01 es domingo (mismos dias usados en test_agenda.py).
MONDAY = "2026-11-02"
SUNDAY = "2026-11-01"


async def _set_monday_working_hours(
    client: AsyncClient, admin_headers: dict[str, str], provider_id: str, *, start: str, end: str
) -> None:
    resp = await client.post(
        f"/api/v1/providers/{provider_id}/working-hours",
        headers=admin_headers,
        json={"weekday": 0, "start_time": start, "end_time": end},
    )
    assert resp.status_code == 201, resp.text


async def test_availability_returns_slots_within_working_hours(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    admin_headers, provider_id, _patient_id = await _setup(client, make_user, clinic, db_session)
    await _set_monday_working_hours(client, admin_headers, provider_id, start="09:00", end="10:00")

    resp = await client.get(
        "/api/v1/appointments/availability",
        headers=admin_headers,
        params={"provider_id": provider_id, "day": MONDAY, "duration_minutes": 30},
    )

    assert resp.status_code == 200
    slots = resp.json()["slots"]
    # Paso de 15 min (agenda/service.py::_FREE_SLOT_STEP_MINUTES): en una ventana de
    # 09:00-10:00 con 30 min de duracion caben 09:00, 09:15 y 09:30 (09:45 ya no).
    assert len(slots) == 3
    assert slots[0].startswith(f"{MONDAY}T09:00:00")
    assert slots[1].startswith(f"{MONDAY}T09:15:00")
    assert slots[2].startswith(f"{MONDAY}T09:30:00")


async def test_availability_excludes_a_slot_already_taken(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    admin_headers, provider_id, patient_id = await _setup(client, make_user, clinic, db_session)
    await _set_monday_working_hours(client, admin_headers, provider_id, start="09:00", end="10:00")

    create_resp = await client.post(
        "/api/v1/appointments",
        headers=admin_headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": f"{MONDAY}T09:00:00+00:00",
            "ends_at": f"{MONDAY}T09:30:00+00:00",
        },
    )
    assert create_resp.status_code == 201, create_resp.text

    resp = await client.get(
        "/api/v1/appointments/availability",
        headers=admin_headers,
        params={"provider_id": provider_id, "day": MONDAY, "duration_minutes": 30},
    )

    slots = resp.json()["slots"]
    assert all(not s.startswith(f"{MONDAY}T09:00:00") for s in slots)
    assert slots[0].startswith(f"{MONDAY}T09:30:00")


async def test_availability_respects_limit(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    admin_headers, provider_id, _patient_id = await _setup(client, make_user, clinic, db_session)
    await _set_monday_working_hours(client, admin_headers, provider_id, start="09:00", end="12:00")

    resp = await client.get(
        "/api/v1/appointments/availability",
        headers=admin_headers,
        params={"provider_id": provider_id, "day": MONDAY, "duration_minutes": 30, "limit": 1},
    )

    assert len(resp.json()["slots"]) == 1


async def test_availability_is_empty_without_working_hours_that_day(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    admin_headers, provider_id, _patient_id = await _setup(client, make_user, clinic, db_session)
    await _set_monday_working_hours(client, admin_headers, provider_id, start="09:00", end="12:00")

    resp = await client.get(
        "/api/v1/appointments/availability",
        headers=admin_headers,
        params={"provider_id": provider_id, "day": SUNDAY, "duration_minutes": 30},
    )

    assert resp.status_code == 200
    assert resp.json()["slots"] == []


async def test_availability_requires_agenda_read_permission(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    admin_headers, provider_id, _patient_id = await _setup(client, make_user, clinic, db_session)
    await _set_monday_working_hours(client, admin_headers, provider_id, start="09:00", end="12:00")

    # caja no tiene agenda.read en la matriz de permisos por defecto
    # (backend/app/modules/iam/permissions_catalog.py).
    await make_user(email="caja@example.com", role_code="caja")
    token = await _login(client, "caja@example.com")

    resp = await client.get(
        "/api/v1/appointments/availability",
        headers=_headers(token, clinic.id),
        params={"provider_id": provider_id, "day": MONDAY, "duration_minutes": 30},
    )

    assert resp.status_code == 403
