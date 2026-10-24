from httpx import AsyncClient

from app.core.config import get_settings


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


async def test_me_reports_ai_enabled_when_enabled(
    client: AsyncClient, make_user, monkeypatch
) -> None:
    monkeypatch.setattr(get_settings(), "ai_enabled", True)
    await make_user(email="odonto@example.com")
    token = await _login(client, "odonto@example.com")

    response = await client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.json()["ai_enabled"] is True


async def test_me_reports_ai_enabled_false_when_disabled(
    client: AsyncClient, make_user, monkeypatch
) -> None:
    """Fase "Publicacion en Hostinger" sec. 6, cambio #4: el frontend usa este
    campo (cargado en cada sesion) para ocultar todo lo de IA sin depender del
    permiso ai.configure, que odontologo/especialista no tienen."""
    monkeypatch.setattr(get_settings(), "ai_enabled", False)
    await make_user(email="odonto@example.com")
    token = await _login(client, "odonto@example.com")

    response = await client.get(
        "/api/v1/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.json()["ai_enabled"] is False
