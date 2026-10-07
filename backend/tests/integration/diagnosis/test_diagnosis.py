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
    return headers, str(patient.id), encounter_resp.json()["id"]


async def test_create_diagnosis_with_tooth_and_surface(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/diagnoses",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "code": "caries",
            "text": "Caries oclusal profunda en 36",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "caries"
    assert body["tooth_fdi"] == 36
    assert body["is_active"] is True


async def test_create_diagnosis_rejects_invalid_tooth(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/diagnoses",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": 19, "text": "Pieza invalida"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_TOOTH"


async def test_diagnosis_without_tooth_is_valid(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/diagnoses",
        headers=headers,
        json={"encounter_id": encounter_id, "text": "Maloclusion clase II"},
    )
    assert response.status_code == 201
    assert response.json()["tooth_fdi"] is None


async def test_annul_diagnosis_requires_reason(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    created = await client.post(
        f"/api/v1/patients/{patient_id}/diagnoses",
        headers=headers,
        json={"encounter_id": encounter_id, "text": "Diagnostico de prueba"},
    )
    item_id = created.json()["id"]

    without_reason = await client.post(
        f"/api/v1/patients/{patient_id}/diagnoses/{item_id}/annul", headers=headers, json={}
    )
    assert without_reason.status_code == 422

    with_reason = await client.post(
        f"/api/v1/patients/{patient_id}/diagnoses/{item_id}/annul",
        headers=headers,
        json={"reason": "Se registro en el paciente equivocado"},
    )
    assert with_reason.status_code == 200
    assert with_reason.json()["is_active"] is False

    listed = await client.get(f"/api/v1/patients/{patient_id}/diagnoses", headers=headers)
    assert listed.json()[0]["is_active"] is False


async def test_create_diagnosis_denied_without_permission(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    await make_user(email="recepcion@example.com", role_code="recepcion")
    recepcion_token = await _login(client, "recepcion@example.com")

    response = await client.post(
        f"/api/v1/patients/{patient_id}/diagnoses",
        headers=_headers(recepcion_token, clinic.id),
        json={"encounter_id": encounter_id, "text": "No deberia poder"},
    )
    assert response.status_code == 403


async def test_create_diagnosis_rejects_a_code_not_in_the_clinic_catalog(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """B1 (Parte B, Fase 12.2): 'Diagnosticos' ya no es un Literal fijo, sino el
    catalogo administrable de la sucursal (el codigo sigue siendo opcional)."""
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/diagnoses",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "code": "no_existe",
            "text": "Diagnostico con codigo invalido",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_DIAGNOSIS_CODE"


async def test_create_diagnosis_without_a_code_still_works(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """El texto del diagnostico siempre es libre: el codigo del catalogo es solo un
    atajo opcional, nunca obligatorio."""
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/diagnoses",
        headers=headers,
        json={"encounter_id": encounter_id, "text": "Diagnostico sin codigo del catalogo"},
    )

    assert response.status_code == 201, response.text
    assert response.json()["code"] is None
