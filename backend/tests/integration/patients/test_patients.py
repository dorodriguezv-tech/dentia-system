import datetime
import io

from httpx import AsyncClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditEvent


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _headers(token: str, clinic_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic_id)}


async def _create_recepcion_token(client: AsyncClient, make_user, clinic) -> str:
    await make_user(email="recepcion@example.com", role_code="recepcion")
    return await _login(client, "recepcion@example.com")


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (20, 20), (10, 20, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


BASIC_PATIENT = {
    "first_name": "Jose",
    "last_name_paternal": "Perez",
    "last_name_maternal": "Gomez",
    "date_of_birth": "1990-05-20",
    "phone": "5555555555",
    "email": "jose.perez@example.com",
}


async def test_create_patient_assigns_expediente_number(
    client: AsyncClient, make_user, clinic
) -> None:
    token = await _create_recepcion_token(client, make_user, clinic)

    response = await client.post(
        "/api/v1/patients", headers=_headers(token, clinic.id), json=BASIC_PATIENT
    )

    assert response.status_code == 201
    body = response.json()
    assert body["expediente_number"] == "000001"
    assert body["full_name"] == "Jose Perez Gomez"
    assert body["status"] == "activo"


async def test_create_patient_denied_without_write_permission(
    client: AsyncClient, make_user, clinic
) -> None:
    # asistente, no odontologo: desde que el odontologo gana patients.write
    # (RBAC real, docs/MATRIZ_PERMISOS.md), asistente es el rol clinico que
    # sigue sin poder dar de alta pacientes.
    await make_user(email="asistente@example.com", role_code="asistente")
    token = await _login(client, "asistente@example.com")

    response = await client.post(
        "/api/v1/patients", headers=_headers(token, clinic.id), json=BASIC_PATIENT
    )

    assert response.status_code == 403


async def test_get_patient_is_audited(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    token = await _create_recepcion_token(client, make_user, clinic)
    create_response = await client.post(
        "/api/v1/patients", headers=_headers(token, clinic.id), json=BASIC_PATIENT
    )
    patient_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/patients/{patient_id}", headers=_headers(token, clinic.id)
    )
    assert response.status_code == 200

    events = (
        (
            await db_session.execute(
                select(AuditEvent).where(
                    AuditEvent.action == "patients.read", AuditEvent.entity_id == patient_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1


async def test_update_status_without_reason_is_rejected(
    client: AsyncClient, make_user, clinic
) -> None:
    token = await _create_recepcion_token(client, make_user, clinic)
    created = await client.post(
        "/api/v1/patients", headers=_headers(token, clinic.id), json=BASIC_PATIENT
    )
    patient_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/patients/{patient_id}",
        headers=_headers(token, clinic.id),
        json={"status": "bloqueado"},
    )
    assert response.status_code == 422


async def test_update_status_with_reason_is_applied_and_audited(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    token = await _create_recepcion_token(client, make_user, clinic)
    created = await client.post(
        "/api/v1/patients", headers=_headers(token, clinic.id), json=BASIC_PATIENT
    )
    patient_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/patients/{patient_id}",
        headers=_headers(token, clinic.id),
        json={"status": "bloqueado", "status_reason": "Adeudo pendiente"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "bloqueado"

    events = (
        (
            await db_session.execute(
                select(AuditEvent).where(
                    AuditEvent.action == "patients.updated", AuditEvent.entity_id == patient_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert events[0].details["status"]["to"] == "bloqueado"
    assert events[0].details["status"]["reason"] == "Adeudo pendiente"


async def test_create_pediatric_patient_without_phone_or_email(
    client: AsyncClient, make_user, clinic
) -> None:
    """Reproduce el reporte del usuario: un paciente pediatrico (menor de edad) sin
    telefono ni correo -- CONFIRMADO que no falla (ambos son opcionales en el
    esquema y en el flujo completo: duplicados -> alta -> contacto de tutor sin
    datos -> lectura -> resumen), igual que para un adulto. Queda como regresion."""
    token = await _create_recepcion_token(client, make_user, clinic)
    recent_dob = (datetime.date.today() - datetime.timedelta(days=365 * 5)).isoformat()

    dup_response = await client.post(
        "/api/v1/patients/duplicates-check",
        headers=_headers(token, clinic.id),
        json={
            "first_name": "Nino",
            "last_name_paternal": "Prueba",
            "last_name_maternal": None,
            "date_of_birth": recent_dob,
            "phone": None,
        },
    )
    assert dup_response.status_code == 200
    assert dup_response.json() == []

    response = await client.post(
        "/api/v1/patients",
        headers=_headers(token, clinic.id),
        json={
            "first_name": "Nino",
            "last_name_paternal": "Prueba",
            "last_name_maternal": None,
            "date_of_birth": recent_dob,
            "phone": None,
            "email": None,
            "address": None,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["phone"] is None
    assert body["email"] is None
    assert body["patient_type"] == "pediatrico"
    patient_id = body["id"]

    contact_response = await client.post(
        f"/api/v1/patients/{patient_id}/contacts",
        headers=_headers(token, clinic.id),
        json={"role": "guardian", "full_name": "Mama de Nino", "phone": None},
    )
    assert contact_response.status_code == 201, contact_response.text

    get_response = await client.get(
        f"/api/v1/patients/{patient_id}", headers=_headers(token, clinic.id)
    )
    assert get_response.status_code == 200

    summary_response = await client.get(
        f"/api/v1/patients/{patient_id}/summary", headers=_headers(token, clinic.id)
    )
    assert summary_response.status_code == 200


async def test_create_patient_computes_patient_type_from_date_of_birth(
    client: AsyncClient, make_user, clinic
) -> None:
    token = await _create_recepcion_token(client, make_user, clinic)

    adult_response = await client.post(
        "/api/v1/patients", headers=_headers(token, clinic.id), json=BASIC_PATIENT
    )
    assert adult_response.json()["patient_type"] == "adulto"

    pediatric_dob = (datetime.date.today() - datetime.timedelta(days=365 * 5)).isoformat()
    pediatric_response = await client.post(
        "/api/v1/patients",
        headers=_headers(token, clinic.id),
        json={**BASIC_PATIENT, "date_of_birth": pediatric_dob, "phone": None, "email": None},
    )
    assert pediatric_response.json()["patient_type"] == "pediatrico"


async def test_create_patient_respects_explicit_patient_type(
    client: AsyncClient, make_user, clinic
) -> None:
    token = await _create_recepcion_token(client, make_user, clinic)

    # Adulto de edad pero marcado explicitamente como "pediatrico" -- se respeta la
    # anotacion manual, no se recalcula a partir de la fecha de nacimiento.
    response = await client.post(
        "/api/v1/patients",
        headers=_headers(token, clinic.id),
        json={**BASIC_PATIENT, "patient_type": "pediatrico"},
    )
    assert response.status_code == 201
    assert response.json()["patient_type"] == "pediatrico"


async def test_update_patient_type_overrides_without_recalculating(
    client: AsyncClient, make_user, clinic
) -> None:
    token = await _create_recepcion_token(client, make_user, clinic)
    created = await client.post(
        "/api/v1/patients", headers=_headers(token, clinic.id), json=BASIC_PATIENT
    )
    patient_id = created.json()["id"]
    assert created.json()["patient_type"] == "adulto"

    corrected = await client.patch(
        f"/api/v1/patients/{patient_id}",
        headers=_headers(token, clinic.id),
        json={"patient_type": "pediatrico"},
    )
    assert corrected.status_code == 200
    assert corrected.json()["patient_type"] == "pediatrico"

    # Una edicion posterior que no menciona patient_type no debe tocarlo (es una
    # anotacion editable, no se recalcula sola).
    unrelated_update = await client.patch(
        f"/api/v1/patients/{patient_id}",
        headers=_headers(token, clinic.id),
        json={"address": "Calle Falsa 123"},
    )
    assert unrelated_update.status_code == 200
    assert unrelated_update.json()["patient_type"] == "pediatrico"


async def test_search_is_accent_and_case_insensitive(
    client: AsyncClient, make_user, clinic
) -> None:
    token = await _create_recepcion_token(client, make_user, clinic)
    await client.post(
        "/api/v1/patients",
        headers=_headers(token, clinic.id),
        json={**BASIC_PATIENT, "first_name": "Jose", "last_name_paternal": "Nunez"},
    )

    response = await client.get(
        "/api/v1/patients/search",
        params={"q": "jose nunez"},
        headers=_headers(token, clinic.id),
    )

    assert response.status_code == 200
    names = [p["full_name"] for p in response.json()]
    assert any("Nunez" in n for n in names)


async def test_search_by_expediente_number(client: AsyncClient, make_user, clinic) -> None:
    token = await _create_recepcion_token(client, make_user, clinic)
    created = await client.post(
        "/api/v1/patients", headers=_headers(token, clinic.id), json=BASIC_PATIENT
    )
    expediente = created.json()["expediente_number"]

    response = await client.get(
        "/api/v1/patients/search",
        params={"q": expediente},
        headers=_headers(token, clinic.id),
    )
    assert response.status_code == 200
    assert any(p["expediente_number"] == expediente for p in response.json())


async def test_duplicates_check_finds_similar_name_same_birthdate(
    client: AsyncClient, make_user, clinic
) -> None:
    token = await _create_recepcion_token(client, make_user, clinic)
    await client.post("/api/v1/patients", headers=_headers(token, clinic.id), json=BASIC_PATIENT)

    response = await client.post(
        "/api/v1/patients/duplicates-check",
        headers=_headers(token, clinic.id),
        json={
            "first_name": "Jose",
            "last_name_paternal": "Peres",
            "last_name_maternal": "Gomes",
            "date_of_birth": "1990-05-20",
        },
    )

    assert response.status_code == 200
    candidates = response.json()
    assert len(candidates) == 1
    assert candidates[0]["expediente_number"] == "000001"


async def test_duplicates_check_without_dob_or_phone_returns_empty(
    client: AsyncClient, make_user, clinic
) -> None:
    token = await _create_recepcion_token(client, make_user, clinic)
    await client.post("/api/v1/patients", headers=_headers(token, clinic.id), json=BASIC_PATIENT)

    response = await client.post(
        "/api/v1/patients/duplicates-check",
        headers=_headers(token, clinic.id),
        json={"first_name": "Jose", "last_name_paternal": "Perez"},
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_contacts_crud_flow(client: AsyncClient, make_user, clinic) -> None:
    token = await _create_recepcion_token(client, make_user, clinic)
    created = await client.post(
        "/api/v1/patients", headers=_headers(token, clinic.id), json=BASIC_PATIENT
    )
    patient_id = created.json()["id"]

    create_contact = await client.post(
        f"/api/v1/patients/{patient_id}/contacts",
        headers=_headers(token, clinic.id),
        json={
            "role": "emergency",
            "full_name": "Ana Perez",
            "relationship_label": "Hermana",
            "phone": "5551112222",
        },
    )
    assert create_contact.status_code == 201
    contact_id = create_contact.json()["id"]

    update_contact = await client.patch(
        f"/api/v1/patients/{patient_id}/contacts/{contact_id}",
        headers=_headers(token, clinic.id),
        json={"phone": "5559998888"},
    )
    assert update_contact.status_code == 200
    assert update_contact.json()["phone"] == "5559998888"

    list_response = await client.get(
        f"/api/v1/patients/{patient_id}/contacts", headers=_headers(token, clinic.id)
    )
    assert len(list_response.json()) == 1

    delete_response = await client.delete(
        f"/api/v1/patients/{patient_id}/contacts/{contact_id}", headers=_headers(token, clinic.id)
    )
    assert delete_response.status_code == 204

    list_after = await client.get(
        f"/api/v1/patients/{patient_id}/contacts", headers=_headers(token, clinic.id)
    )
    assert list_after.json() == []


async def test_photo_upload_wrong_type_rejected(client: AsyncClient, make_user, clinic) -> None:
    token = await _create_recepcion_token(client, make_user, clinic)
    created = await client.post(
        "/api/v1/patients", headers=_headers(token, clinic.id), json=BASIC_PATIENT
    )
    patient_id = created.json()["id"]

    response = await client.post(
        f"/api/v1/patients/{patient_id}/photo",
        headers=_headers(token, clinic.id),
        files={"file": ("foto.txt", b"hola", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_FILE_TYPE"


async def test_photo_upload_and_read(client: AsyncClient, make_user, clinic) -> None:
    token = await _create_recepcion_token(client, make_user, clinic)
    created = await client.post(
        "/api/v1/patients", headers=_headers(token, clinic.id), json=BASIC_PATIENT
    )
    patient_id = created.json()["id"]

    upload = await client.post(
        f"/api/v1/patients/{patient_id}/photo",
        headers=_headers(token, clinic.id),
        files={"file": ("foto.png", _png_bytes(), "image/png")},
    )
    assert upload.status_code == 200
    assert upload.json()["has_photo"] is True

    photo = await client.get(
        f"/api/v1/patients/{patient_id}/photo", headers=_headers(token, clinic.id)
    )
    assert photo.status_code == 200
    assert photo.headers["content-type"] == "image/png"


async def test_list_patients_filters_by_status(client: AsyncClient, make_user, clinic) -> None:
    token = await _create_recepcion_token(client, make_user, clinic)
    created = await client.post(
        "/api/v1/patients", headers=_headers(token, clinic.id), json=BASIC_PATIENT
    )
    patient_id = created.json()["id"]
    await client.patch(
        f"/api/v1/patients/{patient_id}",
        headers=_headers(token, clinic.id),
        json={"status": "inactivo", "status_reason": "Se cambio de clinica"},
    )

    active = await client.get(
        "/api/v1/patients", params={"status": "activo"}, headers=_headers(token, clinic.id)
    )
    inactive = await client.get(
        "/api/v1/patients", params={"status": "inactivo"}, headers=_headers(token, clinic.id)
    )

    assert active.json() == []
    assert len(inactive.json()) == 1


async def _create_provider_and_resource(
    client: AsyncClient, make_user, clinic, admin_token: str
) -> tuple[str, str]:
    headers = _headers(admin_token, clinic.id)
    odonto = await make_user(email="tratante@example.com", role_code="odontologo")
    provider_resp = await client.post(
        "/api/v1/providers", headers=headers, json={"user_id": str(odonto.id)}
    )
    resource_resp = await client.post(
        "/api/v1/resources", headers=headers, json={"name": "Gabinete tratante"}
    )
    return provider_resp.json()["id"], resource_resp.json()["id"]


async def test_create_patient_with_default_resource_and_primary_provider(
    client: AsyncClient, make_user, clinic
) -> None:
    """B3 (Parte B, Fase 12.2): la agenda los preselecciona despues al agendar."""
    await make_user(email="admin@example.com", role_code="admin_clinica")
    admin_token = await _login(client, "admin@example.com")
    provider_id, resource_id = await _create_provider_and_resource(
        client, make_user, clinic, admin_token
    )

    response = await client.post(
        "/api/v1/patients",
        headers=_headers(admin_token, clinic.id),
        json={
            **BASIC_PATIENT,
            "default_resource_id": resource_id,
            "primary_provider_id": provider_id,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["default_resource_id"] == resource_id
    assert body["primary_provider_id"] == provider_id


async def test_create_patient_rejects_a_provider_from_another_clinic(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    from app.modules.iam.models import Clinic, Role, UserClinic

    other_clinic = Clinic(organization_id=clinic.organization_id, name="Otra sucursal")
    db_session.add(other_clinic)
    await db_session.flush()
    admin = await make_user(email="admin@example.com", role_code="admin_clinica")
    admin_role = (
        await db_session.execute(select(Role).where(Role.code == "admin_clinica"))
    ).scalar_one()
    db_session.add(UserClinic(user_id=admin.id, clinic_id=other_clinic.id, role_id=admin_role.id))
    await db_session.commit()

    admin_token = await _login(client, "admin@example.com")
    other_odonto = await make_user(email="ajeno@example.com", role_code="odontologo")
    foreign_provider_resp = await client.post(
        "/api/v1/providers",
        headers=_headers(admin_token, other_clinic.id),
        json={"user_id": str(other_odonto.id)},
    )
    foreign_provider_id = foreign_provider_resp.json()["id"]

    response = await client.post(
        "/api/v1/patients",
        headers=_headers(admin_token, clinic.id),
        json={**BASIC_PATIENT, "primary_provider_id": foreign_provider_id},
    )
    assert response.status_code == 404


async def test_update_patient_care_assignment_without_reason_is_rejected(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    admin_token = await _login(client, "admin@example.com")
    _provider_id, resource_id = await _create_provider_and_resource(
        client, make_user, clinic, admin_token
    )
    created = await client.post(
        "/api/v1/patients", headers=_headers(admin_token, clinic.id), json=BASIC_PATIENT
    )
    patient_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/patients/{patient_id}",
        headers=_headers(admin_token, clinic.id),
        json={"default_resource_id": resource_id},
    )
    assert response.status_code == 422


async def test_update_patient_care_assignment_with_reason_is_applied_and_audited(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    admin_token = await _login(client, "admin@example.com")
    provider_id, resource_id = await _create_provider_and_resource(
        client, make_user, clinic, admin_token
    )
    created = await client.post(
        "/api/v1/patients", headers=_headers(admin_token, clinic.id), json=BASIC_PATIENT
    )
    patient_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/patients/{patient_id}",
        headers=_headers(admin_token, clinic.id),
        json={
            "default_resource_id": resource_id,
            "primary_provider_id": provider_id,
            "care_assignment_reason": "Primera asignacion con el especialista",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["default_resource_id"] == resource_id
    assert body["primary_provider_id"] == provider_id

    events = (
        (
            await db_session.execute(
                select(AuditEvent).where(
                    AuditEvent.action == "patients.updated", AuditEvent.entity_id == patient_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert events[0].details["care_assignment"]["reason"] == (
        "Primera asignacion con el especialista"
    )


async def test_list_patients_mine_only_filters_by_primary_provider(
    client: AsyncClient, make_user, clinic
) -> None:
    """B3: filtro "Mis pacientes" para el rol odontologo."""
    await make_user(email="admin@example.com", role_code="admin_clinica")
    admin_token = await _login(client, "admin@example.com")
    provider_id, _resource_id = await _create_provider_and_resource(
        client, make_user, clinic, admin_token
    )

    mine = await client.post(
        "/api/v1/patients",
        headers=_headers(admin_token, clinic.id),
        json={**BASIC_PATIENT, "primary_provider_id": provider_id},
    )
    assert mine.status_code == 201
    await client.post(
        "/api/v1/patients",
        headers=_headers(admin_token, clinic.id),
        json={
            "first_name": "Ana",
            "last_name_paternal": "Lopez",
            "date_of_birth": "1985-01-01",
        },
    )

    tratante_token = await _login(client, "tratante@example.com")
    mine_only = await client.get(
        "/api/v1/patients",
        params={"mine_only": "true"},
        headers=_headers(tratante_token, clinic.id),
    )
    assert mine_only.status_code == 200
    names = [p["full_name"] for p in mine_only.json()]
    assert names == ["Jose Perez Gomez"]

    all_patients = await client.get("/api/v1/patients", headers=_headers(admin_token, clinic.id))
    assert len(all_patients.json()) == 2


async def test_list_patients_mine_only_is_empty_for_a_role_without_a_provider(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    admin_token = await _login(client, "admin@example.com")
    await client.post(
        "/api/v1/patients", headers=_headers(admin_token, clinic.id), json=BASIC_PATIENT
    )

    response = await client.get(
        "/api/v1/patients",
        params={"mine_only": "true"},
        headers=_headers(admin_token, clinic.id),
    )
    assert response.status_code == 200
    assert response.json() == []
