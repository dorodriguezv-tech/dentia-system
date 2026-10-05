import pyotp
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def test_admin_clinica_without_mfa_is_flagged_as_setup_required(
    client: AsyncClient, make_user
) -> None:
    await make_user(email="admin@example.com", password="Contrasena123", role_code="admin_clinica")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Contrasena123"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["mfa_setup_required"] is True


async def test_odontologo_is_not_flagged_as_setup_required(client: AsyncClient, make_user) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123", role_code="odontologo")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "odonto@example.com", "password": "Contrasena123"},
    )

    assert response.json()["user"]["mfa_setup_required"] is False


async def test_setup_and_enable_mfa_clears_the_flag(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    await make_user(email="admin@example.com", password="Contrasena123", role_code="admin_clinica")
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Contrasena123"},
    )
    access_token = login_response.json().get("access_token")
    assert access_token, "el admin sin MFA debe poder iniciar sesion para poder configurarla"

    headers = {"Authorization": f"Bearer {access_token}"}
    setup_response = await client.post("/api/v1/auth/mfa/setup", headers=headers)
    assert setup_response.status_code == 200
    secret = setup_response.json()["secret"]

    code = pyotp.TOTP(secret).now()
    enable_response = await client.post(
        "/api/v1/auth/mfa/enable", json={"code": code}, headers=headers
    )
    assert enable_response.status_code == 204

    me_response = await client.get("/api/v1/me", headers=headers)
    assert me_response.json()["mfa_setup_required"] is False
