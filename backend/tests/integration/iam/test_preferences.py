from httpx import AsyncClient


async def _access_token_for(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


async def test_get_preferences_creates_defaults_on_first_read(
    client: AsyncClient, make_user
) -> None:
    # B7 (docs/06_APP_MOVIL_V1_1_PARIDAD.md sec. 4): la primera lectura crea la fila
    # con los valores por defecto, sin que nadie tenga que darla de alta antes.
    await make_user(email="odonto@example.com", password="Contrasena123")
    token = await _access_token_for(client, "odonto@example.com", "Contrasena123")

    response = await client.get(
        "/api/v1/me/preferences", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "language": "es-MX",
        "theme": "system",
        "dentia_enabled": True,
        "voice_id": None,
        "speech_rate": 1.0,
        "speech_volume": 1.0,
        "lock_timeout_minutes": 2,
    }


async def test_put_preferences_updates_only_sent_fields(client: AsyncClient, make_user) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")
    token = await _access_token_for(client, "odonto@example.com", "Contrasena123")
    headers = {"Authorization": f"Bearer {token}"}

    first = await client.put(
        "/api/v1/me/preferences",
        headers=headers,
        json={"theme": "dark", "dentia_enabled": False},
    )
    assert first.status_code == 200
    assert first.json()["theme"] == "dark"
    assert first.json()["dentia_enabled"] is False
    assert first.json()["speech_rate"] == 1.0  # no se tocó

    second = await client.put(
        "/api/v1/me/preferences",
        headers=headers,
        json={"voice_id": "es-us-x-esf-local", "speech_rate": 0.85},
    )
    assert second.status_code == 200
    body = second.json()
    assert body["voice_id"] == "es-us-x-esf-local"
    assert body["speech_rate"] == 0.85
    # lo que ya se habia guardado en la llamada anterior persiste
    assert body["theme"] == "dark"
    assert body["dentia_enabled"] is False


async def test_get_preferences_reflects_previous_updates(client: AsyncClient, make_user) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")
    token = await _access_token_for(client, "odonto@example.com", "Contrasena123")
    headers = {"Authorization": f"Bearer {token}"}

    await client.put("/api/v1/me/preferences", headers=headers, json={"lock_timeout_minutes": 5})
    response = await client.get("/api/v1/me/preferences", headers=headers)

    assert response.status_code == 200
    assert response.json()["lock_timeout_minutes"] == 5


async def test_put_preferences_rejects_invalid_theme(client: AsyncClient, make_user) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")
    token = await _access_token_for(client, "odonto@example.com", "Contrasena123")

    response = await client.put(
        "/api/v1/me/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={"theme": "fucsia"},
    )

    assert response.status_code == 422


async def test_put_preferences_rejects_speech_rate_out_of_range(
    client: AsyncClient, make_user
) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")
    token = await _access_token_for(client, "odonto@example.com", "Contrasena123")

    response = await client.put(
        "/api/v1/me/preferences",
        headers={"Authorization": f"Bearer {token}"},
        json={"speech_rate": 5.0},
    )

    assert response.status_code == 422


async def test_preferences_are_per_user(client: AsyncClient, make_user) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")
    await make_user(email="recepcion@example.com", password="Contrasena123", role_code="recepcion")

    token_a = await _access_token_for(client, "odonto@example.com", "Contrasena123")
    token_b = await _access_token_for(client, "recepcion@example.com", "Contrasena123")

    await client.put(
        "/api/v1/me/preferences",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"theme": "dark"},
    )

    response_b = await client.get(
        "/api/v1/me/preferences", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response_b.json()["theme"] == "system"  # el valor por defecto, sin tocar
