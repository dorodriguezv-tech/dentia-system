"""Cuenta de demostracion de tiempo limitado (rol "demo", User.is_sandboxed/expires_at)
-- a peticion del operador: ve y puede usar todo el sistema, pero nada de lo que haga
sobrevive a su sesion, y queda bloqueada sola despues de su fecha limite."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.agenda.models import Provider
from app.modules.iam.models import Clinic, Role, User, UserClinic
from app.modules.patients.models import Patient


async def _make_sandboxed_user(
    db_session: AsyncSession,
    *,
    clinic: Clinic,
    email: str = "demo@prueba.com",
    expires_at: datetime | None = None,
) -> User:
    role = (await db_session.execute(select(Role).where(Role.code == "demo"))).scalar_one()
    user = User(
        email=email,
        full_name="Cuenta de demostracion",
        hashed_password=hash_password("Demo@1234prueba"),
        is_sandboxed=True,
        expires_at=expires_at,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(UserClinic(user_id=user.id, clinic_id=clinic.id, role_id=role.id))
    await db_session.commit()
    return user


@pytest.mark.asyncio
async def test_login_as_sandboxed_user_seeds_a_baseline_patient(
    client: AsyncClient, db_session: AsyncSession, clinic: Clinic
) -> None:
    await _make_sandboxed_user(db_session, clinic=clinic)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "demo@prueba.com", "password": "Demo@1234prueba"},
    )

    assert response.status_code == 200, response.text
    patients = (
        await db_session.execute(select(Patient).where(Patient.clinic_id == clinic.id))
    ).scalars().all()
    assert len(patients) == 1
    providers = (
        await db_session.execute(select(Provider).where(Provider.clinic_id == clinic.id))
    ).scalars().all()
    assert len(providers) == 1


@pytest.mark.asyncio
async def test_login_wipes_whatever_the_previous_session_created(
    client: AsyncClient, db_session: AsyncSession, clinic: Clinic
) -> None:
    await _make_sandboxed_user(db_session, clinic=clinic)

    first = await client.post(
        "/api/v1/auth/login",
        json={"email": "demo@prueba.com", "password": "Demo@1234prueba"},
    )
    assert first.status_code == 200
    token = first.json()["access_token"]

    create_response = await client.post(
        "/api/v1/patients",
        headers={"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)},
        json={
            "first_name": "Paciente",
            "last_name_paternal": "Temporal",
            "date_of_birth": "2000-01-01",
        },
    )
    assert create_response.status_code == 201, create_response.text

    patients_before = (
        await db_session.execute(select(Patient).where(Patient.clinic_id == clinic.id))
    ).scalars().all()
    assert len(patients_before) == 2  # el de ejemplo + el que acabamos de crear

    second = await client.post(
        "/api/v1/auth/login",
        json={"email": "demo@prueba.com", "password": "Demo@1234prueba"},
    )
    assert second.status_code == 200

    patients_after = (
        await db_session.execute(select(Patient).where(Patient.clinic_id == clinic.id))
    ).scalars().all()
    assert len(patients_after) == 1
    assert all(p.full_name != "Paciente Temporal" for p in patients_after)


@pytest.mark.asyncio
async def test_logout_also_resets_the_demo_clinic(
    client: AsyncClient, db_session: AsyncSession, clinic: Clinic
) -> None:
    await _make_sandboxed_user(db_session, clinic=clinic)

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "demo@prueba.com", "password": "Demo@1234prueba"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    refresh_token = login_response.json()["refresh_token"]

    create_response = await client.post(
        "/api/v1/patients",
        headers={"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)},
        json={
            "first_name": "Paciente",
            "last_name_paternal": "Temporal",
            "date_of_birth": "2000-01-01",
        },
    )
    assert create_response.status_code == 201, create_response.text

    logout_response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_token}
    )
    assert logout_response.status_code == 204

    patients_after = (
        await db_session.execute(select(Patient).where(Patient.clinic_id == clinic.id))
    ).scalars().all()
    assert len(patients_after) == 1


@pytest.mark.asyncio
async def test_login_after_expires_at_is_rejected_and_deactivates_the_account(
    client: AsyncClient, db_session: AsyncSession, clinic: Clinic
) -> None:
    user = await _make_sandboxed_user(
        db_session, clinic=clinic, expires_at=datetime.now(UTC) - timedelta(days=1)
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "demo@prueba.com", "password": "Demo@1234prueba"},
    )

    assert response.status_code == 401
    await db_session.refresh(user)
    assert user.is_active is False


@pytest.mark.asyncio
async def test_sandboxed_actor_cannot_really_delete_or_edit_a_user(
    client: AsyncClient, db_session: AsyncSession, clinic: Clinic, make_user
) -> None:
    await _make_sandboxed_user(db_session, clinic=clinic)
    target = await make_user(email="otro@example.com", role_code="recepcion")
    target_id = target.id  # ver nota en login() sobre expire_on_commit

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "demo@prueba.com", "password": "Demo@1234prueba"},
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    delete_response = await client.delete(f"/api/v1/users/{target_id}", headers=headers)
    assert delete_response.status_code == 204

    update_response = await client.patch(
        f"/api/v1/users/{target_id}", headers=headers, json={"full_name": "Nombre Hackeado"}
    )
    assert update_response.status_code == 200

    still_there = await db_session.get(User, target_id)
    assert still_there is not None
    assert still_there.full_name != "Nombre Hackeado"
    membership = (
        await db_session.execute(
            select(UserClinic).where(
                UserClinic.user_id == target_id, UserClinic.clinic_id == clinic.id
            )
        )
    ).scalar_one_or_none()
    assert membership is not None

    photo_response = await client.post(
        f"/api/v1/users/{target_id}/photo",
        headers=headers,
        files={"file": ("foto.png", b"", "image/png")},
    )
    assert photo_response.status_code == 200
    assert photo_response.json()["has_photo"] is False

    still_there_again = await db_session.get(User, target_id)
    assert still_there_again is not None
    assert still_there_again.photo_path is None
