from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import RefreshToken, User


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> dict:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()


async def test_changes_the_password_and_the_new_one_logs_in(
    client: AsyncClient, make_user
) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")
    tokens = await _login(client, "odonto@example.com")

    response = await client.put(
        "/api/v1/me/password",
        json={"current_password": "Contrasena123", "new_password": "NuevaClaveSegura99"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 204
    login_with_new = await client.post(
        "/api/v1/auth/login",
        json={"email": "odonto@example.com", "password": "NuevaClaveSegura99"},
    )
    assert login_with_new.status_code == 200
    login_with_old = await client.post(
        "/api/v1/auth/login",
        json={"email": "odonto@example.com", "password": "Contrasena123"},
    )
    assert login_with_old.status_code == 401


async def test_wrong_current_password_is_rejected(client: AsyncClient, make_user) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")
    tokens = await _login(client, "odonto@example.com")

    response = await client.put(
        "/api/v1/me/password",
        json={"current_password": "incorrecta", "new_password": "NuevaClaveSegura99"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


async def test_rejects_reusing_the_current_password(client: AsyncClient, make_user) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")
    tokens = await _login(client, "odonto@example.com")

    response = await client.put(
        "/api/v1/me/password",
        json={"current_password": "Contrasena123", "new_password": "Contrasena123"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "PASSWORD_REUSED"


async def test_rejects_reusing_a_recent_password_from_history(
    client: AsyncClient, make_user
) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")
    tokens = await _login(client, "odonto@example.com")

    first_change = await client.put(
        "/api/v1/me/password",
        json={"current_password": "Contrasena123", "new_password": "SegundaClaveSegura1"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert first_change.status_code == 204

    tokens2 = await _login(client, "odonto@example.com", password="SegundaClaveSegura1")
    second_change = await client.put(
        "/api/v1/me/password",
        json={"current_password": "SegundaClaveSegura1", "new_password": "Contrasena123"},
        headers={"Authorization": f"Bearer {tokens2['access_token']}"},
    )

    assert second_change.status_code == 400
    assert second_change.json()["code"] == "PASSWORD_REUSED"


async def test_rejects_a_weak_new_password(client: AsyncClient, make_user) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")
    tokens = await _login(client, "odonto@example.com")

    response = await client.put(
        "/api/v1/me/password",
        json={"current_password": "Contrasena123", "new_password": "short1"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert response.status_code == 422


async def test_revokes_existing_refresh_tokens(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", password="Contrasena123")
    user_id = user.id
    tokens = await _login(client, "odonto@example.com")

    await client.put(
        "/api/v1/me/password",
        json={"current_password": "Contrasena123", "new_password": "NuevaClaveSegura99"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == 401

    db_session.expire_all()
    rows = (
        await db_session.execute(select(RefreshToken).where(RefreshToken.user_id == user_id))
    ).scalars().all()
    assert all(r.revoked_at is not None for r in rows)


async def test_password_history_caps_at_five_entries(
    client: AsyncClient, make_user, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", password="Contrasena123")
    user_id = user.id
    current_password = "Contrasena123"

    for i in range(7):
        tokens = await _login(client, "odonto@example.com", password=current_password)
        new_password = f"ClaveNumero{i}Segura"
        response = await client.put(
            "/api/v1/me/password",
            json={"current_password": current_password, "new_password": new_password},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code == 204
        current_password = new_password

    db_session.expire_all()
    refreshed = (
        await db_session.execute(select(User).where(User.id == user_id))
    ).scalar_one()
    assert len(refreshed.password_history) == 5
    assert verify_password(current_password, refreshed.hashed_password)
