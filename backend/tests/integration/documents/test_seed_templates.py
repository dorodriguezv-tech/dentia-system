from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.rules import TEMPLATE_CODES
from app.seed import DOCUMENT_TEMPLATE_SEEDS, _seed_document_templates


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _headers(token: str, clinic_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic_id)}


def test_document_template_seeds_cover_every_catalog_code() -> None:
    """A6: si se agrega un codigo nuevo al catalogo (TEMPLATE_CODES) y se olvida
    sembrar su ejemplo, el selector de "Firmar y generar PDF" se queda vacio para ese
    codigo otra vez -- esta prueba falla primero para que no pase desapercibido."""
    seeded_codes = {code for code, _, _ in DOCUMENT_TEMPLATE_SEEDS}
    assert seeded_codes == set(TEMPLATE_CODES)


async def test_clinic_without_seeded_templates_has_an_empty_selector(
    client: AsyncClient, make_user, clinic
) -> None:
    """Reproduce A6: antes de sembrar, el selector de plantillas estaba vacio y
    "Firmar y generar PDF" nunca podia habilitarse."""
    await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")

    response = await client.get("/api/v1/document-templates", headers=_headers(token, clinic.id))

    assert response.status_code == 200
    assert response.json() == []


async def test_seeding_fills_the_selector_with_one_example_per_code(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    admin_token = await _login(client, "admin@example.com")
    admin_id_response = await client.get("/api/v1/me", headers=_headers(admin_token, clinic.id))
    admin_id = admin_id_response.json()["id"]

    await _seed_document_templates(db_session, clinic_id=clinic.id, actor_id=admin_id)

    await make_user(email="odonto@example.com", role_code="odontologo")
    odonto_token = await _login(client, "odonto@example.com")
    response = await client.get(
        "/api/v1/document-templates", headers=_headers(odonto_token, clinic.id)
    )

    assert response.status_code == 200
    codes = {t["code"] for t in response.json()}
    assert codes == set(TEMPLATE_CODES)
    assert all("Ejemplo" in t["name"] for t in response.json())
