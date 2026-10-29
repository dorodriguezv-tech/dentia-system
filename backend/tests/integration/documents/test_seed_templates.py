from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.documents.default_templates import DEFAULT_TEMPLATES
from app.modules.documents.models import DocumentTemplate
from app.modules.documents.rules import LEGACY_EXAMPLE_TEMPLATE_CODES, TEMPLATE_CODES
from app.seed import _seed_document_templates


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _headers(token: str, clinic_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic_id)}


def test_document_template_seeds_cover_every_catalog_code() -> None:
    """A6: si se agrega un codigo nuevo al catalogo (TEMPLATE_CODES) y se olvida
    sembrar su formato real (default_templates.py), el selector de "Firmar y
    generar PDF" se queda vacio para ese codigo otra vez -- esta prueba falla
    primero para que no pase desapercibido."""
    seeded_codes = {code for code, _, _ in DEFAULT_TEMPLATES}
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


async def test_seeding_fills_the_selector_with_one_template_per_code(
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
    # Ya no son plantillas de ejemplo: son los 24 formatos oficiales reales.
    assert all(t["name"] for t in response.json())


async def test_seeding_retires_legacy_example_codes_without_a_real_replacement(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """general/extraccion/anestesia no tienen formato real equivalente: tras
    sembrar, quedan retirados (is_current=False) y no aparecen en el selector
    -- regla 7 de CLAUDE.md, no se borran filas."""
    await make_user(email="admin2@example.com", role_code="admin_clinica")
    admin_token = await _login(client, "admin2@example.com")
    admin_id = (await client.get("/api/v1/me", headers=_headers(admin_token, clinic.id))).json()[
        "id"
    ]

    # Simula una clinica con los 4 codigos de ejemplo ya sembrados antes de esta
    # integracion (mismo escenario que una BD existente) -- se insertan los
    # modelos directo, sin pasar por el schema de la API: "general" ya no es
    # un TemplateCode valido, el endpoint lo rechazaria con 422.
    for code in LEGACY_EXAMPLE_TEMPLATE_CODES:
        db_session.add(
            DocumentTemplate(
                clinic_id=clinic.id,
                code=code,
                name=f"Ejemplo — {code}",
                version=1,
                html_content="<p>Ejemplo</p>",
                is_current=True,
                created_by=admin_id,
            )
        )
    await db_session.commit()

    await _seed_document_templates(db_session, clinic_id=clinic.id, actor_id=admin_id)

    response = await client.get(
        "/api/v1/document-templates", headers=_headers(admin_token, clinic.id)
    )
    current_codes = {t["code"] for t in response.json()}
    assert "general" not in current_codes
    assert "extraccion" not in current_codes
    assert "anestesia" not in current_codes
    # "endodoncia" si queda, pero con el contenido real (no el de ejemplo).
    endodoncia = next(t for t in response.json() if t["code"] == "endodoncia")
    assert "Ejemplo" not in endodoncia["name"]
