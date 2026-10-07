from httpx import AsyncClient


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _headers(token: str, clinic_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic_id)}


async def test_admin_can_list_appointment_types(client: AsyncClient, make_user, clinic) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")

    response = await client.get(
        "/api/v1/catalogs/appointment_type", headers=_headers(token, clinic.id)
    )

    assert response.status_code == 200
    codes = {item["code"] for item in response.json()}
    assert "consulta" in codes
    assert "limpieza" in codes


async def test_odontologo_can_read_findings_catalog_without_catalogs_manage(
    client: AsyncClient, make_user, clinic
) -> None:
    """A1 del diseño original (B1): quien ya puede usar el catalogo en su pantalla
    (odontogram.read) debe poder leerlo aqui, sin el permiso de administrarlo."""
    await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")

    response = await client.get(
        "/api/v1/catalogs/odontogram_finding", headers=_headers(token, clinic.id)
    )

    assert response.status_code == 200
    codes = {item["code"] for item in response.json()}
    assert "caries" in codes


async def test_recepcion_cannot_read_odontogram_findings_catalog(
    client: AsyncClient, make_user, clinic
) -> None:
    """Recepcion no tiene odontogram.read ni catalogs.manage."""
    await make_user(email="recepcion@example.com", role_code="recepcion")
    token = await _login(client, "recepcion@example.com")

    response = await client.get(
        "/api/v1/catalogs/odontogram_finding", headers=_headers(token, clinic.id)
    )

    assert response.status_code == 403


async def test_odontologo_cannot_create_catalog_items(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")

    response = await client.post(
        "/api/v1/catalogs/diagnosis",
        headers=_headers(token, clinic.id),
        json={"code": "nuevo_dx", "name": "Nuevo diagnostico"},
    )

    assert response.status_code == 403


async def test_admin_creates_a_new_appointment_type_and_it_appears_immediately(
    client: AsyncClient, make_user, clinic
) -> None:
    """Criterio de aceptacion de B1: 'el administrador crea el tipo de consulta
    Valoracion ortodoncia - 45 min y aparece de inmediato al agendar'."""
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = _headers(token, clinic.id)

    create_response = await client.post(
        "/api/v1/catalogs/appointment_type",
        headers=headers,
        json={
            "code": "valoracion_ortodoncia",
            "name": "Valoracion ortodoncia",
            "extra": {"default_minutes": 45},
        },
    )
    assert create_response.status_code == 201

    list_response = await client.get("/api/v1/catalogs/appointment_type", headers=headers)
    names = {item["code"]: item for item in list_response.json()}
    assert names["valoracion_ortodoncia"]["extra"]["default_minutes"] == 45


async def test_creating_a_duplicate_code_fails(client: AsyncClient, make_user, clinic) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = _headers(token, clinic.id)

    response = await client.post(
        "/api/v1/catalogs/appointment_type",
        headers=headers,
        json={"code": "consulta", "name": "Otra consulta"},
    )

    assert response.status_code == 409


async def test_deactivating_an_item_hides_it_from_the_default_listing_but_keeps_it_for_admin(
    client: AsyncClient, make_user, clinic
) -> None:
    """Criterio de aceptacion de B1: 'desactivar un hallazgo lo oculta del menu
    rapido, pero los registros historicos lo siguen mostrando' -- aqui se cubre la
    parte del catalogo: la lista normal ya no lo trae, pero sigue existiendo."""
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = _headers(token, clinic.id)

    items = (await client.get("/api/v1/catalogs/odontogram_finding", headers=headers)).json()
    caries_id = next(item["id"] for item in items if item["code"] == "caries")

    patch_response = await client.patch(
        f"/api/v1/catalogs/odontogram_finding/{caries_id}",
        headers=headers,
        json={"is_active": False},
    )
    assert patch_response.status_code == 200

    active_only = (await client.get("/api/v1/catalogs/odontogram_finding", headers=headers)).json()
    assert "caries" not in {item["code"] for item in active_only}

    with_inactive = (
        await client.get(
            "/api/v1/catalogs/odontogram_finding?include_inactive=true", headers=headers
        )
    ).json()
    caries_item = next(item for item in with_inactive if item["code"] == "caries")
    assert caries_item["is_active"] is False


async def test_a_non_admin_requesting_inactive_items_silently_gets_only_active(
    client: AsyncClient, make_user, clinic
) -> None:
    """El flag `include_inactive` no es una fuga de permisos: sin catalogs.manage se
    ignora en silencio (nunca se revela que un elemento esta desactivado)."""
    await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")

    response = await client.get(
        "/api/v1/catalogs/odontogram_finding?include_inactive=true",
        headers=_headers(token, clinic.id),
    )

    assert response.status_code == 200
    assert all(item["is_active"] for item in response.json())


async def test_cannot_update_the_code_or_catalog_type_of_an_item(
    client: AsyncClient, make_user, clinic
) -> None:
    """code/catalog_type son inmutables (los usa la IA y los reportes) -- el esquema
    de actualizacion ni siquiera los acepta."""
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = _headers(token, clinic.id)

    items = (await client.get("/api/v1/catalogs/diagnosis", headers=headers)).json()
    item = next(i for i in items if i["code"] == "caries")

    response = await client.patch(
        f"/api/v1/catalogs/diagnosis/{item['id']}",
        headers=headers,
        json={"name": "Caries dental (editado)"},
    )

    assert response.status_code == 200
    assert response.json()["code"] == "caries"
    assert response.json()["name"] == "Caries dental (editado)"


async def test_invalid_catalog_type_is_rejected(client: AsyncClient, make_user, clinic) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")

    response = await client.get(
        "/api/v1/catalogs/not_a_real_catalog", headers=_headers(token, clinic.id)
    )

    assert response.status_code == 400


async def test_export_csv_includes_inactive_items(client: AsyncClient, make_user, clinic) -> None:
    """Pendiente de B1 (Parte B, Fase 12.2): exportar/importar por CSV."""
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = _headers(token, clinic.id)

    items = (await client.get("/api/v1/catalogs/diagnosis", headers=headers)).json()
    item = next(i for i in items if i["code"] == "caries")
    await client.patch(
        f"/api/v1/catalogs/diagnosis/{item['id']}", headers=headers, json={"is_active": False}
    )

    response = await client.get("/api/v1/catalogs/diagnosis/export", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "caries" in response.text
    assert "False" in response.text


async def test_export_without_catalogs_manage_is_forbidden(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")

    response = await client.get(
        "/api/v1/catalogs/diagnosis/export", headers=_headers(token, clinic.id)
    )

    assert response.status_code == 403


async def test_import_csv_creates_and_updates_items(client: AsyncClient, make_user, clinic) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = _headers(token, clinic.id)

    csv_content = (
        "code,name,is_active,sort_order,extra\n"
        "caries,Caries dental (importada),True,0,{}\n"
        "nuevo_diagnostico,Diagnostico nuevo por CSV,True,5,{}\n"
    )
    response = await client.post(
        "/api/v1/catalogs/diagnosis/import",
        headers=headers,
        files={"file": ("diagnosis.csv", csv_content.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created"] == 1
    assert body["updated"] == 1
    assert body["errors"] == []

    items = (await client.get("/api/v1/catalogs/diagnosis", headers=headers)).json()
    by_code = {i["code"]: i for i in items}
    assert by_code["caries"]["name"] == "Caries dental (importada)"
    assert by_code["nuevo_diagnostico"]["name"] == "Diagnostico nuevo por CSV"


async def test_import_csv_reports_errors_per_row_without_aborting(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = _headers(token, clinic.id)

    csv_content = (
        "code,name,is_active,sort_order,extra\n"
        "Codigo Invalido,Nombre,True,0,{}\n"
        "bueno,Diagnostico bueno,True,0,{}\n"
    )
    response = await client.post(
        "/api/v1/catalogs/diagnosis/import",
        headers=headers,
        files={"file": ("diagnosis.csv", csv_content.encode("utf-8"), "text/csv")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created"] == 1
    assert len(body["errors"]) == 1

    items = (await client.get("/api/v1/catalogs/diagnosis", headers=headers)).json()
    assert any(i["code"] == "bueno" for i in items)


async def test_import_csv_without_catalogs_manage_is_forbidden(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")

    response = await client.post(
        "/api/v1/catalogs/diagnosis/import",
        headers=_headers(token, clinic.id),
        files={"file": ("diagnosis.csv", b"code,name\nx,y\n", "text/csv")},
    )

    assert response.status_code == 403
