import base64
import hashlib
import io
import uuid

from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patients.schemas import PatientCreateRequest
from app.modules.patients.service import create_patient


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _headers(token: str, clinic_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic_id)}


def _signature_base64() -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (100, 40), (5, 5, 5)).save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


async def _setup(client: AsyncClient, make_user, clinic, db_session: AsyncSession):
    await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)

    patient = await create_patient(
        db_session,
        clinic_id=clinic.id,
        data=PatientCreateRequest(
            first_name="Jose", last_name_paternal="Perez", date_of_birth="1990-05-20"
        ),
        actor_id=None,
    )
    encounter_resp = await client.post(
        "/api/v1/encounters", headers=headers, json={"patient_id": str(patient.id)}
    )
    assert encounter_resp.status_code == 201, encounter_resp.text
    encounter_id = encounter_resp.json()["id"]

    template_resp = await client.post(
        "/api/v1/document-templates",
        headers=headers,
        json={
            "code": "general",
            "name": "Consentimiento general",
            "html_content": "<p>Autorizo el tratamiento de {{paciente.nombre}}.</p>",
        },
    )
    assert template_resp.status_code == 201, template_resp.text
    return headers, str(patient.id), encounter_id


async def test_create_template_then_a_new_version_retires_the_old_one(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, _patient_id, _encounter_id = await _setup(client, make_user, clinic, db_session)

    second = await client.post(
        "/api/v1/document-templates",
        headers=headers,
        json={
            "code": "general",
            "name": "Consentimiento general v2",
            "html_content": "<p>Nuevo texto</p>",
        },
    )
    assert second.status_code == 201
    assert second.json()["version"] == 2

    current = await client.get("/api/v1/document-templates", headers=headers)
    general = [t for t in current.json() if t["code"] == "general"]
    assert len(general) == 1
    assert general[0]["version"] == 2

    history = await client.get("/api/v1/document-templates/general/history", headers=headers)
    assert [v["version"] for v in history.json()] == [2, 1]
    assert history.json()[1]["is_current"] is False


async def test_create_consent_generates_pdf_with_hash(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/consents",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "template_code": "general",
            "signer_name": "Jose Perez",
            "signer_relationship": "paciente",
            "signature_png_base64": _signature_base64(),
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body["content_hash"]) == 64
    assert body["is_active"] is True

    pdf_resp = await client.get(f"/api/v1/consents/{body['id']}/pdf", headers=headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")

    # W3 (docs/CAMBIOS_WEB_MARCA.md): un consentimiento firmado no se regenera al
    # leerlo (regla 7: los documentos firmados no se sobrescriben); el pie de pagina
    # de marca se agrega solo al firmar, nunca despues. Dos lecturas devuelven el
    # mismo PDF, y su hash coincide con el que quedo guardado al firmar.
    pdf_resp_again = await client.get(f"/api/v1/consents/{body['id']}/pdf", headers=headers)
    assert pdf_resp_again.content == pdf_resp.content
    assert hashlib.sha256(pdf_resp.content).hexdigest() == body["content_hash"]


async def test_create_consent_without_a_configured_template_fails(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    await make_user(email="odonto2@example.com", role_code="odontologo")
    token = await _login(client, "odonto2@example.com")
    headers = _headers(token, clinic.id)

    patient = await create_patient(
        db_session,
        clinic_id=clinic.id,
        data=PatientCreateRequest(
            first_name="Ana", last_name_paternal="Diaz", date_of_birth="1995-01-01"
        ),
        actor_id=None,
    )
    encounter_resp = await client.post(
        "/api/v1/encounters", headers=headers, json={"patient_id": str(patient.id)}
    )
    encounter_id = encounter_resp.json()["id"]

    response = await client.post(
        f"/api/v1/patients/{patient.id}/consents",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "template_code": "extraccion",
            "signer_name": "Ana Diaz",
            "signer_relationship": "paciente",
            "signature_png_base64": _signature_base64(),
        },
    )
    assert response.status_code == 404


async def test_consent_rejects_both_procedure_and_plan_link(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/consents",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "template_code": "general",
            "procedure_planned_id": str(uuid.uuid4()),
            "treatment_plan_id": str(uuid.uuid4()),
            "signer_name": "Jose Perez",
            "signer_relationship": "paciente",
            "signature_png_base64": _signature_base64(),
        },
    )
    assert response.status_code == 422


async def test_annul_consent_requires_reason_and_keeps_pdf(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    created = await client.post(
        f"/api/v1/patients/{patient_id}/consents",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "template_code": "general",
            "signer_name": "Jose Perez",
            "signer_relationship": "paciente",
            "signature_png_base64": _signature_base64(),
        },
    )
    consent_id = created.json()["id"]

    without_reason = await client.post(
        f"/api/v1/consents/{consent_id}/annul", headers=headers, json={}
    )
    assert without_reason.status_code == 422

    with_reason = await client.post(
        f"/api/v1/consents/{consent_id}/annul",
        headers=headers,
        json={"reason": "Firmado por error en el paciente equivocado"},
    )
    assert with_reason.status_code == 200
    assert with_reason.json()["is_active"] is False

    pdf_resp = await client.get(f"/api/v1/consents/{consent_id}/pdf", headers=headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.content.startswith(b"%PDF")


async def test_sign_consent_denied_without_documents_sign_permission(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    await make_user(email="recepcion@example.com", role_code="recepcion")
    recepcion_token = await _login(client, "recepcion@example.com")

    response = await client.post(
        f"/api/v1/patients/{patient_id}/consents",
        headers=_headers(recepcion_token, clinic.id),
        json={
            "encounter_id": encounter_id,
            "template_code": "general",
            "signer_name": "Jose Perez",
            "signer_relationship": "paciente",
            "signature_png_base64": _signature_base64(),
        },
    )
    assert response.status_code == 403
