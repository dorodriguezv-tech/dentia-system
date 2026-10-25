from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.iam.models import Clinic, Organization, Role, UserClinic


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


async def test_new_odontologo_gets_a_provider_automatically(
    client: AsyncClient, make_user, clinic: Clinic
) -> None:
    """A1: un odontologo nuevo debe aparecer de inmediato en el selector de la agenda.

    Reportado dos veces ("usuarios nuevos no aparecen para elegir"): crear un usuario
    con rol odontologo/especialista no creaba su Provider (entidad separada de User
    desde la Fase 6), asi que la agenda nunca lo listaba.
    """
    await make_user(email="admin@example.com", password="Contrasena123", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    create_response = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "nuevo.odontologo@example.com",
            "full_name": "Nueva Odontologa",
            "password": "Contrasena123",
            "role_code": "odontologo",
            "professional_license": "1234567",
        },
    )
    assert create_response.status_code == 201

    providers_response = await client.get("/api/v1/providers", headers=headers)
    assert providers_response.status_code == 200
    names = [p["full_name"] for p in providers_response.json()]
    assert "Nueva Odontologa" in names


async def test_new_recepcion_user_does_not_get_a_provider(
    client: AsyncClient, make_user, clinic: Clinic
) -> None:
    """Recepcion no atiende pacientes: no debe aparecer en el selector de profesionales."""
    await make_user(email="admin@example.com", password="Contrasena123", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "nueva.recepcion@example.com",
            "full_name": "Nueva Recepcionista",
            "password": "Contrasena123",
            "role_code": "recepcion",
        },
    )

    providers_response = await client.get("/api/v1/providers", headers=headers)
    names = [p["full_name"] for p in providers_response.json()]
    assert "Nueva Recepcionista" not in names


async def test_changing_role_to_odontologo_creates_a_provider(
    client: AsyncClient, make_user, clinic: Clinic
) -> None:
    """Un usuario que ya existia (p.ej. asistente) y es promovido a odontologo tambien
    debe aparecer en la agenda, sin pasos manuales."""
    await make_user(email="admin@example.com", password="Contrasena123", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    create_response = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "asistente@example.com",
            "full_name": "Asistente Promovida",
            "password": "Contrasena123",
            "role_code": "asistente",
        },
    )
    user_id = create_response.json()["user"]["id"]

    await client.patch(
        f"/api/v1/users/{user_id}",
        headers=headers,
        json={"role_code": "especialista"},
    )

    providers_response = await client.get("/api/v1/providers", headers=headers)
    names = [p["full_name"] for p in providers_response.json()]
    assert "Asistente Promovida" in names


async def test_deactivating_an_odontologo_hides_their_provider(
    client: AsyncClient, make_user, clinic: Clinic
) -> None:
    """Al desactivar al usuario, su Provider se desactiva (no se borra: tiene citas)."""
    await make_user(email="admin@example.com", password="Contrasena123", role_code="admin_clinica")
    token = await _login(client, "admin@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)}

    create_response = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "odontologo.baja@example.com",
            "full_name": "Odontologo De Baja",
            "password": "Contrasena123",
            "role_code": "odontologo",
            "professional_license": "1234567",
        },
    )
    user_id = create_response.json()["user"]["id"]

    providers_before = await client.get("/api/v1/providers", headers=headers)
    assert "Odontologo De Baja" in [p["full_name"] for p in providers_before.json()]

    await client.patch(
        f"/api/v1/users/{user_id}",
        headers=headers,
        json={"is_active": False},
    )

    providers_after = await client.get("/api/v1/providers", headers=headers)
    assert "Odontologo De Baja" not in [p["full_name"] for p in providers_after.json()]


async def test_creating_an_odontologo_with_a_default_resource_sets_it_on_their_provider(
    client: AsyncClient, make_user, clinic: Clinic
) -> None:
    """B2 (Parte B, Fase 12.2): el formulario de alta deja elegir, por sucursal, un
    gabinete por defecto -- la agenda lo preselecciona despues al agendar."""
    await make_user(email="admin@example.com", role_code="admin_clinica")
    headers = {
        "Authorization": f"Bearer {await _login(client, 'admin@example.com')}",
        "X-Clinic-Id": str(clinic.id),
    }

    resource_resp = await client.post(
        "/api/v1/resources", headers=headers, json={"name": "Gabinete A"}
    )
    resource_id = resource_resp.json()["id"]

    create_response = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "nuevo2@example.com",
            "full_name": "Nuevo Odontologo",
            "password": "Contrasena123",
            "role_code": "odontologo",
            "professional_license": "1234567",
            "default_resource_id": resource_id,
        },
    )
    assert create_response.status_code == 201, create_response.text

    providers = (await client.get("/api/v1/providers", headers=headers)).json()
    created = next(p for p in providers if p["full_name"] == "Nuevo Odontologo")
    assert created["default_resource_id"] == resource_id


async def test_creating_a_user_in_additional_clinics_assigns_them_there_too(
    client: AsyncClient, make_user, clinic: Clinic, db_session: AsyncSession
) -> None:
    """B2: el administrador puede elegir mas de una sucursal al dar de alta."""
    other_clinic = Clinic(organization_id=clinic.organization_id, name="Sucursal Norte")
    db_session.add(other_clinic)
    await db_session.flush()

    admin = await make_user(email="admin@example.com", role_code="admin_clinica")
    admin_role = (
        await db_session.execute(select(Role).where(Role.code == "admin_clinica"))
    ).scalar_one()
    db_session.add(UserClinic(user_id=admin.id, clinic_id=other_clinic.id, role_id=admin_role.id))
    await db_session.commit()

    headers = {
        "Authorization": f"Bearer {await _login(client, 'admin@example.com')}",
        "X-Clinic-Id": str(clinic.id),
    }

    create_response = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "multi@example.com",
            "full_name": "Profesional Multisucursal",
            "password": "Contrasena123",
            "role_code": "odontologo",
            "professional_license": "1234567",
            "additional_clinics": [{"clinic_id": str(other_clinic.id)}],
        },
    )
    assert create_response.status_code == 201, create_response.text
    user_id = create_response.json()["user"]["id"]

    other_headers = {
        "Authorization": headers["Authorization"],
        "X-Clinic-Id": str(other_clinic.id),
    }
    other_users = (await client.get("/api/v1/users", headers=other_headers)).json()
    assert any(u["user"]["id"] == user_id for u in other_users)

    other_providers = (await client.get("/api/v1/providers", headers=other_headers)).json()
    assert any(p["full_name"] == "Profesional Multisucursal" for p in other_providers)


async def test_cannot_assign_a_new_user_to_a_clinic_without_manage_users_permission_there(
    client: AsyncClient, make_user, clinic: Clinic, db_session: AsyncSession
) -> None:
    """B2: elegir una sucursal ajena (donde el administrador no administra usuarios)
    no debe ser posible solo por conocer su id."""
    organization = Organization(name="Otra organizacion")
    db_session.add(organization)
    await db_session.flush()
    foreign_clinic = Clinic(organization_id=organization.id, name="Sucursal ajena")
    db_session.add(foreign_clinic)
    await db_session.commit()

    await make_user(email="admin@example.com", role_code="admin_clinica")
    headers = {
        "Authorization": f"Bearer {await _login(client, 'admin@example.com')}",
        "X-Clinic-Id": str(clinic.id),
    }

    response = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "intento@example.com",
            "full_name": "Intento Fallido",
            "password": "Contrasena123",
            "role_code": "odontologo",
            "professional_license": "1234567",
            "additional_clinics": [{"clinic_id": str(foreign_clinic.id)}],
        },
    )
    assert response.status_code == 403


async def test_admin_can_edit_their_own_clinics_contact_info(
    client: AsyncClient, make_user, clinic: Clinic
) -> None:
    """Pendiente de B1 (Parte B, Fase 12.2): antes no habia ninguna forma de editar
    una sucursal. `catalogs.manage` (admin_clinica) ya puede editar la propia --
    distinto de `iam.manage_clinics` (solo superadmin, crear/administrar entre
    organizaciones)."""
    await make_user(email="admin@example.com", role_code="admin_clinica")
    headers = {
        "Authorization": f"Bearer {await _login(client, 'admin@example.com')}",
        "X-Clinic-Id": str(clinic.id),
    }

    response = await client.patch(
        "/api/v1/clinics/current",
        headers=headers,
        json={"address": "Av. Siempre Viva 123", "phone": "5555555555"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["address"] == "Av. Siempre Viva 123"
    assert response.json()["phone"] == "5555555555"
    assert response.json()["name"] == clinic.name


async def test_clinic_has_a_default_timezone(
    client: AsyncClient, make_user, clinic: Clinic
) -> None:
    """Bug #42 de docs/PENDIENTES_CLINICOS.md: una sucursal nueva ya trae una
    zona horaria razonable (Mexico), sin que haga falta configurarla a mano."""
    await make_user(email="admin@example.com", role_code="admin_clinica")
    headers = {
        "Authorization": f"Bearer {await _login(client, 'admin@example.com')}",
        "X-Clinic-Id": str(clinic.id),
    }
    response = await client.patch("/api/v1/clinics/current", headers=headers, json={})
    assert response.status_code == 200, response.text
    assert response.json()["timezone"] == "America/Mexico_City"


async def test_admin_can_change_the_clinic_timezone(
    client: AsyncClient, make_user, clinic: Clinic
) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    headers = {
        "Authorization": f"Bearer {await _login(client, 'admin@example.com')}",
        "X-Clinic-Id": str(clinic.id),
    }
    response = await client.patch(
        "/api/v1/clinics/current", headers=headers, json={"timezone": "America/Tijuana"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["timezone"] == "America/Tijuana"


async def test_updating_the_clinic_with_an_invalid_timezone_is_rejected(
    client: AsyncClient, make_user, clinic: Clinic
) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    headers = {
        "Authorization": f"Bearer {await _login(client, 'admin@example.com')}",
        "X-Clinic-Id": str(clinic.id),
    }
    response = await client.patch(
        "/api/v1/clinics/current", headers=headers, json={"timezone": "No/Existe"}
    )
    assert response.status_code == 422


async def test_non_admin_cannot_edit_the_clinic(
    client: AsyncClient, make_user, clinic: Clinic
) -> None:
    await make_user(email="odonto@example.com", role_code="odontologo")
    headers = {
        "Authorization": f"Bearer {await _login(client, 'odonto@example.com')}",
        "X-Clinic-Id": str(clinic.id),
    }

    response = await client.patch(
        "/api/v1/clinics/current", headers=headers, json={"name": "Otro nombre"}
    )

    assert response.status_code == 403


async def test_duplicate_clinic_in_additional_clinics_is_rejected(
    client: AsyncClient, make_user, clinic: Clinic
) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    headers = {
        "Authorization": f"Bearer {await _login(client, 'admin@example.com')}",
        "X-Clinic-Id": str(clinic.id),
    }

    response = await client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "duplicado@example.com",
            "full_name": "Duplicado",
            "password": "Contrasena123",
            "role_code": "odontologo",
            "professional_license": "1234567",
            "additional_clinics": [{"clinic_id": str(clinic.id)}],
        },
    )
    assert response.status_code == 400


async def test_admin_can_change_a_users_login_email(
    client: AsyncClient, make_user, clinic: Clinic
) -> None:
    """El formulario de editar usuario no mostraba el correo de acceso en ningun
    rol (reportado por el operador) -- ademas de agregarlo en pantalla, el backend
    debe aceptar el cambio."""
    await make_user(email="admin@example.com", password="Contrasena123", role_code="admin_clinica")
    target = await make_user(email="viejo@example.com", role_code="recepcion")
    target_id = target.id  # ver nota en login() sobre expire_on_commit
    headers = {
        "Authorization": f"Bearer {await _login(client, 'admin@example.com')}",
        "X-Clinic-Id": str(clinic.id),
    }

    response = await client.patch(
        f"/api/v1/users/{target_id}",
        headers=headers,
        json={"email": "nuevo@example.com"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["user"]["email"] == "nuevo@example.com"


async def test_cannot_change_a_users_email_to_one_already_taken(
    client: AsyncClient, make_user, clinic: Clinic
) -> None:
    await make_user(email="admin@example.com", password="Contrasena123", role_code="admin_clinica")
    target = await make_user(email="objetivo@example.com", role_code="recepcion")
    target_id = target.id  # ver nota en login() sobre expire_on_commit
    await make_user(email="ocupado@example.com", role_code="caja")
    headers = {
        "Authorization": f"Bearer {await _login(client, 'admin@example.com')}",
        "X-Clinic-Id": str(clinic.id),
    }

    response = await client.patch(
        f"/api/v1/users/{target_id}",
        headers=headers,
        json={"email": "ocupado@example.com"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "EMAIL_TAKEN"
