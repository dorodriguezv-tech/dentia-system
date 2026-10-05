import pyotp
from httpx import AsyncClient

from app.modules.iam.models import User


async def test_login_success_returns_tokens(client: AsyncClient, make_user) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "odonto@example.com", "password": "Contrasena123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == "odonto@example.com"


async def test_login_invalid_password_is_rejected(client: AsyncClient, make_user) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "odonto@example.com", "password": "incorrecta"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


async def test_login_is_rate_limited_after_too_many_failures(
    client: AsyncClient, make_user
) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")

    for _ in range(5):
        await client.post(
            "/api/v1/auth/login",
            json={"email": "odonto@example.com", "password": "incorrecta"},
        )

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "odonto@example.com", "password": "Contrasena123"},
    )

    assert response.status_code == 429
    assert response.json()["code"] == "RATE_LIMITED"


async def test_refresh_rotates_token_and_old_one_stops_working(
    client: AsyncClient, make_user
) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "odonto@example.com", "password": "Contrasena123"},
    )
    old_refresh = login_response.json()["refresh_token"]

    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert refresh_response.status_code == 200
    new_refresh = refresh_response.json()["refresh_token"]
    assert new_refresh != old_refresh

    reuse_response = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse_response.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient, make_user) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "odonto@example.com", "password": "Contrasena123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    logout_response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_token}
    )
    assert logout_response.status_code == 204

    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 401


async def test_login_with_mfa_enabled_requires_second_step(client: AsyncClient, make_user) -> None:
    secret = pyotp.random_base32()
    await make_user(
        email="admin@example.com",
        password="Contrasena123",
        role_code="admin_clinica",
        mfa_enabled=True,
        mfa_secret=secret,
    )

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Contrasena123"},
    )
    assert login_response.status_code == 200
    body = login_response.json()
    assert body["mfa_required"] is True
    mfa_token = body["mfa_token"]

    code = pyotp.TOTP(secret).now()
    mfa_response = await client.post(
        "/api/v1/auth/login/mfa", json={"mfa_token": mfa_token, "code": code}
    )
    assert mfa_response.status_code == 200
    assert mfa_response.json()["access_token"]


async def test_login_with_mfa_wrong_code_is_rejected(client: AsyncClient, make_user) -> None:
    secret = pyotp.random_base32()
    await make_user(
        email="admin@example.com",
        password="Contrasena123",
        role_code="admin_clinica",
        mfa_enabled=True,
        mfa_secret=secret,
    )

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Contrasena123"},
    )
    mfa_token = login_response.json()["mfa_token"]

    mfa_response = await client.post(
        "/api/v1/auth/login/mfa", json={"mfa_token": mfa_token, "code": "000000"}
    )
    assert mfa_response.status_code == 401


async def _access_token_for(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


async def test_permission_denied_for_role_without_grant(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="recepcion@example.com", password="Contrasena123", role_code="recepcion")
    token = await _access_token_for(client, "recepcion@example.com", "Contrasena123")

    response = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)},
        json={
            "email": "nuevo@example.com",
            "full_name": "Nuevo Usuario",
            "password": "Contrasena123",
            "role_code": "recepcion",
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


async def test_admin_can_create_user_in_own_clinic(
    client: AsyncClient, make_user, clinic, db_session
) -> None:
    await make_user(
        email="admin@example.com",
        password="Contrasena123",
        role_code="admin_clinica",
        mfa_enabled=False,
    )
    token = await _access_token_for(client, "admin@example.com", "Contrasena123")

    response = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)},
        json={
            "email": "nuevo@example.com",
            "full_name": "Nuevo Usuario",
            "password": "Contrasena123",
            "role_code": "recepcion",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "nuevo@example.com"
    assert body["role"]["code"] == "recepcion"

    created = (
        await db_session.execute(User.__table__.select().where(User.email == "nuevo@example.com"))
    ).first()
    assert created is not None
