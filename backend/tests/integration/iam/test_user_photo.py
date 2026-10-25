"""Foto de perfil del usuario (pedida junto con editar/borrar usuario): se puede
subir, se ve al consultar al usuario y sobrevive a una relectura."""

import io

from httpx import AsyncClient
from PIL import Image

from app.modules.iam.models import Clinic


def _headers(token: str, clinic_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic_id)}


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), (10, 20, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


async def test_admin_uploads_and_reads_a_users_photo(
    client: AsyncClient, make_user, clinic: Clinic
) -> None:
    await make_user(email="admin@example.com", password="Contrasena123", role_code="admin_clinica")
    target = await make_user(email="objetivo@example.com", role_code="recepcion")
    target_id = target.id  # ver nota en login() sobre expire_on_commit
    headers = _headers(await _login(client, "admin@example.com"), clinic.id)

    upload = await client.post(
        f"/api/v1/users/{target_id}/photo",
        headers=headers,
        files={"file": ("foto.png", _png_bytes(), "image/png")},
    )
    assert upload.status_code == 200, upload.text
    assert upload.json()["has_photo"] is True

    photo = await client.get(f"/api/v1/users/{target_id}/photo", headers=headers)
    assert photo.status_code == 200
    assert photo.headers["content-type"] == "image/png"


async def test_user_photo_wrong_type_rejected(
    client: AsyncClient, make_user, clinic: Clinic
) -> None:
    await make_user(email="admin@example.com", password="Contrasena123", role_code="admin_clinica")
    target = await make_user(email="objetivo@example.com", role_code="recepcion")
    target_id = target.id
    headers = _headers(await _login(client, "admin@example.com"), clinic.id)

    response = await client.post(
        f"/api/v1/users/{target_id}/photo",
        headers=headers,
        files={"file": ("foto.txt", b"hola", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_FILE_TYPE"


async def test_user_without_manage_users_permission_cannot_upload_a_photo(
    client: AsyncClient, make_user, clinic: Clinic
) -> None:
    await make_user(email="recepcion@example.com", role_code="recepcion")
    target = await make_user(email="objetivo@example.com", role_code="caja")
    target_id = target.id
    headers = _headers(await _login(client, "recepcion@example.com"), clinic.id)

    response = await client.post(
        f"/api/v1/users/{target_id}/photo",
        headers=headers,
        files={"file": ("foto.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 403
