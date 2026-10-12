import pyotp
from httpx import AsyncClient

from app.modules.iam.models import User


async def test_login_success_returns_tokens(client: AsyncClient, make_user) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "odonto@example.com", "password": "Contrasena123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == "odonto@example.com"


async def test_login_invalid_password_is_rejected(client: AsyncClient, make_user) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "odonto@example.com", "password": "incorrecta"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


async def test_login_is_rate_limited_after_too_many_failures(
    client: AsyncClient, make_user
) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")

    for _ in range(5):
        await client.post(
            "/api/v1/auth/login",
            json={"email": "odonto@example.com", "password": "incorrecta"},
        )

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "odonto@example.com", "password": "Contrasena123"},
    )

    assert response.status_code == 429
    assert response.json()["code"] == "RATE_LIMITED"


async def test_refresh_rotates_token_and_old_one_stops_working(
    client: AsyncClient, make_user
) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "odonto@example.com", "password": "Contrasena123"},
    )
    old_refresh = login_response.json()["refresh_token"]

    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": old_refresh}
    )
    assert refresh_response.status_code == 200
    new_refresh = refresh_response.json()["refresh_token"]
    assert new_refresh != old_refresh

    reuse_response = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reuse_response.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient, make_user) -> None:
    await make_user(email="odonto@example.com", password="Contrasena123")
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "odonto@example.com", "password": "Contrasena123"},
    )
    refresh_token = login_response.json()["refresh_token"]

    logout_response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": refresh_token}
    )
    assert logout_response.status_code == 204

    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 401


async def test_login_with_mfa_required_returns_mfa_token_shape(
    client: AsyncClient, make_user, monkeypatch
) -> None:
    # B5 (docs/05_APP_MOVIL.md Sec. 7): la app movil espera exactamente estos
    # nombres de campo para el segundo paso ({"mfa_required": true, "mfa_token":
    # "..."} y luego POST /auth/login/mfa con {mfa_token, code}); ya es lo que
    # produce el backend, esta prueba lo fija activando MFA_ENABLED (rules.py
    # lo trae en False globalmente mientras no se termina el flujo completo).
    from app.modules.iam import rules as iam_rules

    monkeypatch.setattr(iam_rules, "MFA_ENABLED", True)
    secret = pyotp.random_base32()
    await make_user(
        email="admin@example.com",
        password="Contrasena123",
        role_code="admin_clinica",
        mfa_enabled=True,
        mfa_secret=secret,
    )

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Contrasena123"},
    )
    assert login_response.status_code == 200
    body = login_response.json()
    assert body["mfa_required"] is True
    assert body["mfa_token"]
    assert "access_token" not in body

    code = pyotp.TOTP(secret).now()
    mfa_response = await client.post(
        "/api/v1/auth/login/mfa",
        json={"mfa_token": body["mfa_token"], "code": code},
    )
    assert mfa_response.status_code == 200
    mfa_body = mfa_response.json()
    assert mfa_body["access_token"]
    assert mfa_body["refresh_token"]


async def test_login_skips_mfa_step_while_globally_disabled(client: AsyncClient, make_user) -> None:
    # rules.MFA_ENABLED esta en False temporalmente (ver ese archivo): incluso una
    # cuenta que ya tiene mfa_enabled/mfa_secret en la base entra directo, sin pedir
    # el codigo. Cuando se reactive (MFA_ENABLED = True), este login debe volver a
    # devolver mfa_required=True y un mfa_token en vez de los tokens de sesion.
    secret = pyotp.random_base32()
    await make_user(
        email="admin@example.com",
        password="Contrasena123",
        role_code="admin_clinica",
        mfa_enabled=True,
        mfa_secret=secret,
    )

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Contrasena123"},
    )
    assert login_response.status_code == 200
    body = login_response.json()
    assert body["access_token"]
    assert "mfa_token" not in body


async def test_my_clinics_includes_clinic_name_and_permissions(
    client: AsyncClient, make_user, clinic
) -> None:
    # B4 (docs/05_APP_MOVIL.md Sec. 7): la app movil necesita saber que botones
    # mostrar sin adivinar el rol; el backend sigue autorizando cada peticion.
    await make_user(email="odonto@example.com", password="Contrasena123", role_code="odontologo")
    token = await _access_token_for(client, "odonto@example.com", "Contrasena123")

    response = await client.get("/api/v1/me/clinics", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    item = body[0]
    assert item["clinic_name"] == clinic.name
    assert item["clinic"]["id"] == str(clinic.id)
    assert item["role"]["code"] == "odontologo"
    assert "agenda.write" in item["permissions"]
    assert "patients.write" not in item["permissions"]  # RBAC real: el odontologo no lo tiene


async def _access_token_for(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


async def test_permission_denied_for_role_without_grant(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="recepcion@example.com", password="Contrasena123", role_code="recepcion")
    token = await _access_token_for(client, "recepcion@example.com", "Contrasena123")

    response = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)},
        json={
            "email": "nuevo@example.com",
            "full_name": "Nuevo Usuario",
            "password": "Contrasena123",
            "role_code": "recepcion",
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


async def test_admin_can_create_user_in_own_clinic(
    client: AsyncClient, make_user, clinic, db_session
) -> None:
    await make_user(
        email="admin@example.com",
        password="Contrasena123",
        role_code="admin_clinica",
        mfa_enabled=False,
    )
    token = await _access_token_for(client, "admin@example.com", "Contrasena123")

    response = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic.id)},
        json={
            "email": "nuevo@example.com",
            "full_name": "Nuevo Usuario",
            "password": "Contrasena123",
            "role_code": "recepcion",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "nuevo@example.com"
    assert body["role"]["code"] == "recepcion"

    created = (
        await db_session.execute(User.__table__.select().where(User.email == "nuevo@example.com"))
    ).first()
    assert created is not None
