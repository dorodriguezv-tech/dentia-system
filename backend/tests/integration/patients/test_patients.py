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
    await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")

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
