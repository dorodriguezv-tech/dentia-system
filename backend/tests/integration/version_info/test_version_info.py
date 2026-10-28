from httpx import AsyncClient

from app.core.config import get_settings


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


async def test_version_info_requires_authentication(client: AsyncClient, clinic) -> None:
    response = await client.get("/api/v1/version-info", headers={"X-Clinic-Id": str(clinic.id)})
    assert response.status_code == 401


async def test_version_info_denied_without_permission(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    response = await client.get("/api/v1/version-info", headers=headers)
    assert response.status_code == 403


async def test_admin_can_read_version_info(
    client: AsyncClient, make_user, clinic, monkeypatch
) -> None:
    monkeypatch.setattr(get_settings(), "app_version", "1.2.3")
    monkeypatch.setattr(get_settings(), "environment", "production")

    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    response = await client.get("/api/v1/version-info", headers=headers)
    assert response.status_code == 200
    assert response.json() == {"version": "1.2.3", "environment": "production"}


async def test_superadmin_can_read_version_info(
    client: AsyncClient, make_user, clinic, monkeypatch
) -> None:
    monkeypatch.setattr(get_settings(), "app_version", "2.0.0")

    await make_user(email="super@example.com", role_code="superadmin")
    token = await _login(client, "super@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    response = await client.get("/api/v1/version-info", headers=headers)
    assert response.status_code == 200
    assert response.json()["version"] == "2.0.0"
