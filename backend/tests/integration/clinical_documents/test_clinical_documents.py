from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patients.schemas import PatientCreateRequest
from app.modules.patients.service import create_patient


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _headers(token: str, clinic_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic_id)}


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
    return headers, str(patient.id), encounter_id


# --------------------------------------------------------------------------- receta


async def test_create_prescription_assigns_sequential_folio_and_generates_pdf(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    first = await client.post(
        f"/api/v1/patients/{patient_id}/clinical-documents/prescriptions",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "diagnostico": "Caries en pieza 36",
            "medications": [{"nombre": "Amoxicilina 500mg", "detalle": "Cada 8 horas por 7 dias"}],
        },
    )
    assert first.status_code == 201, first.text
    assert first.json()["folio"] == "RX-000001"

    second = await client.post(
        f"/api/v1/patients/{patient_id}/clinical-documents/prescriptions",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "diagnostico": "Control de rutina",
            "medications": [{"nombre": "Ibuprofeno 400mg", "detalle": "Cada 8 horas por 3 dias"}],
        },
    )
    assert second.status_code == 201
    assert second.json()["folio"] == "RX-000002"

    pdf_resp = await client.get(
        f"/api/v1/clinical-documents/prescriptions/{second.json()['id']}/pdf", headers=headers
    )
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert pdf_resp.content.startswith(b"%PDF")


async def test_prescription_requires_at_least_one_medication(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/clinical-documents/prescriptions",
        headers=headers,
        json={"encounter_id": encounter_id, "diagnostico": "Caries", "medications": []},
    )
    assert response.status_code == 422


async def test_annul_prescription_requires_reason(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    created = await client.post(
        f"/api/v1/patients/{patient_id}/clinical-documents/prescriptions",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "diagnostico": "Caries",
            "medications": [{"nombre": "Amoxicilina", "detalle": "Cada 8 horas"}],
        },
    )
    item_id = created.json()["id"]

    without_reason = await client.post(
        f"/api/v1/clinical-documents/prescriptions/{item_id}/annul", headers=headers, json={}
    )
    assert without_reason.status_code == 422

    with_reason = await client.post(
        f"/api/v1/clinical-documents/prescriptions/{item_id}/annul",
        headers=headers,
        json={"reason": "Diagnostico capturado por error"},
    )
    assert with_reason.status_code == 200
    assert with_reason.json()["is_active"] is False

    # Regla 7-like: la receta anulada se sigue pudiendo imprimir (auditoria,
    # no se borra fisicamente -- regla 2 de CLAUDE.md).
    pdf_resp = await client.get(
        f"/api/v1/clinical-documents/prescriptions/{item_id}/pdf", headers=headers
    )
    assert pdf_resp.status_code == 200


async def test_create_prescription_denied_without_documents_write(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    await make_user(email="recepcion@example.com", role_code="recepcion")
    recepcion_token = await _login(client, "recepcion@example.com")

    response = await client.post(
        f"/api/v1/patients/{patient_id}/clinical-documents/prescriptions",
        headers=_headers(recepcion_token, clinic.id),
        json={
            "encounter_id": encounter_id,
            "diagnostico": "Caries",
            "medications": [{"nombre": "Amoxicilina", "detalle": "Cada 8 horas"}],
        },
    )
    assert response.status_code == 403


# --------------------------------------------------------------------------- referencia


async def test_create_referral_note_and_generate_pdf(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/clinical-documents/referral-notes",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "diagnosticos": "Caries profunda pieza 36",
            "motivo_interconsulta": "Valoracion por endodoncia",
            "establecimiento_receptor": "Clinica Especializada XYZ",
        },
    )
    assert response.status_code == 201, response.text
    item = response.json()
    assert item["motivo_interconsulta"] == "Valoracion por endodoncia"

    pdf_resp = await client.get(
        f"/api/v1/clinical-documents/referral-notes/{item['id']}/pdf", headers=headers
    )
    assert pdf_resp.status_code == 200
    assert pdf_resp.content.startswith(b"%PDF")


async def test_referral_note_requires_motivo_interconsulta(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/clinical-documents/referral-notes",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "motivo_interconsulta": "",
            "establecimiento_receptor": "Clinica XYZ",
        },
    )
    assert response.status_code == 422


# ------------------------------------------------------------------- contrarreferencia


async def test_create_counter_referral_note_linked_to_referral(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    referral = await client.post(
        f"/api/v1/patients/{patient_id}/clinical-documents/referral-notes",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "motivo_interconsulta": "Valoracion por endodoncia",
            "establecimiento_receptor": "Clinica Especializada XYZ",
        },
    )
    referral_id = referral.json()["id"]

    response = await client.post(
        f"/api/v1/patients/{patient_id}/clinical-documents/counter-referral-notes",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "referral_note_id": referral_id,
            "motivo_contrarreferencia": "Tratamiento de endodoncia concluido",
            "establecimiento_emisor": "Clinica Especializada XYZ",
        },
    )
    assert response.status_code == 201, response.text
    item = response.json()
    assert item["referral_note_id"] == referral_id

    pdf_resp = await client.get(
        f"/api/v1/clinical-documents/counter-referral-notes/{item['id']}/pdf", headers=headers
    )
    assert pdf_resp.status_code == 200
    assert pdf_resp.content.startswith(b"%PDF")


async def test_counter_referral_note_rejects_referral_from_another_patient(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    other_patient = await create_patient(
        db_session,
        clinic_id=clinic.id,
        data=PatientCreateRequest(
            first_name="Ana", last_name_paternal="Diaz", date_of_birth="1995-01-01"
        ),
        actor_id=None,
    )
    other_encounter_resp = await client.post(
        "/api/v1/encounters", headers=headers, json={"patient_id": str(other_patient.id)}
    )
    other_encounter_id = other_encounter_resp.json()["id"]
    referral = await client.post(
        f"/api/v1/patients/{other_patient.id}/clinical-documents/referral-notes",
        headers=headers,
        json={
            "encounter_id": other_encounter_id,
            "motivo_interconsulta": "Valoracion",
            "establecimiento_receptor": "Clinica XYZ",
        },
    )
    referral_id = referral.json()["id"]

    response = await client.post(
        f"/api/v1/patients/{patient_id}/clinical-documents/counter-referral-notes",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "referral_note_id": referral_id,
            "motivo_contrarreferencia": "Respuesta",
            "establecimiento_emisor": "Clinica XYZ",
        },
    )
    assert response.status_code == 404
