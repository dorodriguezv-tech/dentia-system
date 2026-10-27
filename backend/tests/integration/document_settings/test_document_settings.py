import io

from httpx import AsyncClient
from PIL import Image


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _png_bytes(size: tuple[int, int] = (20, 20)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (43, 179, 163)).save(buffer, format="PNG")
    return buffer.getvalue()


async def test_get_document_settings_without_data_returns_empty(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    response = await client.get("/api/v1/document-settings", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["institutional_title"] is None
    assert body["place_label"] is None
    assert body["has_logo_left"] is False
    assert body["has_logo_right"] is False


async def test_get_document_settings_requires_authentication(client: AsyncClient, clinic) -> None:
    response = await client.get(
        "/api/v1/document-settings", headers={"X-Clinic-Id": str(clinic.id)}
    )
    assert response.status_code == 401


async def test_update_document_settings_denied_without_permission(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    response = await client.put(
        "/api/v1/document-settings",
        headers=headers,
        json={"institutional_title": "Clinica X", "place_label": "CDMX"},
    )
    assert response.status_code == 403


async def test_admin_can_update_document_settings(client: AsyncClient, make_user, clinic) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    response = await client.put(
        "/api/v1/document-settings",
        headers=headers,
        json={
            "institutional_title": "Clinica Odontologica Escuela Militar",
            "place_label": "Ciudad de Mexico",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["institutional_title"] == "Clinica Odontologica Escuela Militar"
    assert body["place_label"] == "Ciudad de Mexico"

    read_back = await client.get("/api/v1/document-settings", headers=headers)
    assert read_back.json()["institutional_title"] == "Clinica Odontologica Escuela Militar"


async def test_admin_can_upload_left_and_right_logos(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    left = await client.post(
        "/api/v1/document-settings/logo-left",
        headers=headers,
        files={"file": ("logo.png", _png_bytes(), "image/png")},
    )
    assert left.status_code == 200
    assert left.json()["has_logo_left"] is True
    assert left.json()["has_logo_right"] is False

    right = await client.post(
        "/api/v1/document-settings/logo-right",
        headers=headers,
        files={"file": ("logo.png", _png_bytes(), "image/png")},
    )
    assert right.status_code == 200
    assert right.json()["has_logo_right"] is True

    left_response = await client.get("/api/v1/document-settings/logo-left", headers=headers)
    assert left_response.status_code == 200
    assert left_response.headers["content-type"] == "image/png"

    right_response = await client.get("/api/v1/document-settings/logo-right", headers=headers)
    assert right_response.status_code == 200


async def test_logo_without_configuration_returns_404(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    response = await client.get("/api/v1/document-settings/logo-left", headers=headers)
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


async def test_logo_too_large_is_rejected(client: AsyncClient, make_user, clinic) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    oversized = b"0" * (1_000_000 + 1)
    response = await client.post(
        "/api/v1/document-settings/logo-left",
        headers=headers,
        files={"file": ("logo.png", oversized, "image/png")},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "FILE_TOO_LARGE"


async def test_logo_wrong_type_is_rejected(client: AsyncClient, make_user, clinic) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    response = await client.post(
        "/api/v1/document-settings/logo-left",
        headers=headers,
        files={"file": ("logo.txt", b"hola", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_FILE_TYPE"
