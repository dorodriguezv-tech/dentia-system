import io

from httpx import AsyncClient
from PIL import Image

from app.modules.branding.presets import full_palette


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _png_bytes(size: tuple[int, int] = (20, 20)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (43, 179, 163)).save(buffer, format="PNG")
    return buffer.getvalue()


async def test_get_branding_without_data_returns_default_preset(
    client: AsyncClient, clinic
) -> None:
    response = await client.get("/api/v1/branding")

    assert response.status_code == 200
    body = response.json()
    assert body["preset"] == "menta_clinica"
    assert body["colors"]["primary"] == "#1E7D72"
    assert body["logo_url"] is None


async def test_put_branding_requires_authentication(client: AsyncClient, clinic) -> None:
    response = await client.put(
        "/api/v1/branding",
        headers={"X-Clinic-Id": str(clinic.id)},
        json={"display_name": "Clinica X", "preset": "azul_sereno"},
    )
    assert response.status_code == 401


async def test_put_branding_denied_without_permission(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")

    response = await client.put(
        "/api/v1/branding",
        headers={"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)},
        json={"display_name": "Clinica X", "preset": "azul_sereno"},
    )
    assert response.status_code == 403


async def test_admin_can_change_preset(client: AsyncClient, make_user, clinic) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    response = await client.put(
        "/api/v1/branding",
        headers=headers,
        json={"display_name": "Clinica Demo", "preset": "azul_sereno"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["preset"] == "azul_sereno"
    assert body["colors"] == full_palette("azul_sereno")

    public = await client.get("/api/v1/branding")
    assert public.json()["display_name"] == "Clinica Demo"


async def test_custom_colors_with_low_contrast_return_warning(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    low_contrast_colors = {**full_palette("menta_clinica"), "text": "#EEEEEE", "bg": "#FFFFFF"}

    response = await client.put(
        "/api/v1/branding",
        headers=headers,
        json={"display_name": "Clinica Demo", "preset": "custom", "colors": low_contrast_colors},
    )

    assert response.status_code == 200
    warnings = response.json()["contrast_warnings"]
    assert any(w["pair"] == "texto/fondo" for w in warnings)


async def test_custom_preset_without_colors_is_rejected(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    response = await client.put(
        "/api/v1/branding",
        headers=headers,
        json={"display_name": "Clinica Demo", "preset": "custom"},
    )

    assert response.status_code == 422


async def test_logo_too_large_is_rejected(client: AsyncClient, make_user, clinic) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    oversized = b"0" * (1_000_000 + 1)
    response = await client.post(
        "/api/v1/branding/logo",
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
        "/api/v1/branding/logo",
        headers=headers,
        files={"file": ("logo.txt", b"hola", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_FILE_TYPE"


async def test_logo_corrupt_image_is_rejected(client: AsyncClient, make_user, clinic) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    response = await client.post(
        "/api/v1/branding/logo",
        headers=headers,
        files={"file": ("logo.png", b"not a real png", "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_IMAGE"


async def test_valid_png_logo_is_accepted_and_served(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    response = await client.post(
        "/api/v1/branding/logo",
        headers=headers,
        files={"file": ("logo.png", _png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["logo_url"] == "/api/v1/branding/logo"
    assert body["favicon_url"] == "/api/v1/branding/favicon"

    logo_response = await client.get("/api/v1/branding/logo")
    assert logo_response.status_code == 200
    assert logo_response.headers["content-type"] == "image/png"

    favicon_response = await client.get("/api/v1/branding/favicon")
    assert favicon_response.status_code == 200
    with Image.open(io.BytesIO(favicon_response.content)) as favicon:
        assert favicon.size == (64, 64)


async def test_svg_logo_with_script_is_sanitized(client: AsyncClient, make_user, clinic) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    malicious_svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script>'
        b'<circle cx="5" cy="5" r="4" onclick="alert(1)" /></svg>'
    )

    response = await client.post(
        "/api/v1/branding/logo",
        headers=headers,
        files={"file": ("logo.svg", malicious_svg, "image/svg+xml")},
    )
    assert response.status_code == 200

    logo_response = await client.get("/api/v1/branding/logo")
    assert b"<script" not in logo_response.content
    assert b"onclick" not in logo_response.content


async def test_logo_without_authentication_is_rejected(client: AsyncClient, clinic) -> None:
    response = await client.post(
        "/api/v1/branding/logo",
        headers={"X-Clinic-Id": str(clinic.id)},
        files={"file": ("logo.png", _png_bytes(), "image/png")},
    )
    assert response.status_code == 401
