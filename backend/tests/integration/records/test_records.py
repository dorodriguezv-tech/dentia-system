from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patients.schemas import PatientCreateRequest
from app.modules.patients.service import create_patient


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _headers(token: str, clinic_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic_id)}


async def _odontologo_token(client: AsyncClient, make_user) -> str:
    await make_user(email="odonto@example.com", role_code="odontologo")
    return await _login(client, "odonto@example.com")


async def _setup(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> tuple[dict, str, str]:
    token = await _odontologo_token(client, make_user)
    headers = _headers(token, clinic.id)
    patient = await create_patient(
        db_session,
        clinic_id=clinic.id,
        data=PatientCreateRequest(
            first_name="Jose", last_name_paternal="Perez", date_of_birth="1990-05-20"
        ),
        actor_id=None,
    )
    encounter = await client.post(
        "/api/v1/encounters", headers=headers, json={"patient_id": str(patient.id)}
    )
    return headers, str(patient.id), encounter.json()["id"]


async def test_create_allergy_appears_in_alerts(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/allergies",
        headers=headers,
        json={"encounter_id": encounter_id, "substance": "Penicilina", "severity": "leve"},
    )
    assert created.status_code == 201

    alerts = await client.get(f"/api/v1/patients/{patient_id}/alerts", headers=headers)
    assert alerts.json() == ["Alergia: Penicilina"]


async def test_annul_allergy_requires_reason_and_removes_alert(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    allergy = (
        await client.post(
            f"/api/v1/patients/{patient_id}/allergies",
            headers=headers,
            json={"encounter_id": encounter_id, "substance": "Latex", "severity": "moderada"},
        )
    ).json()

    missing_reason = await client.post(
        f"/api/v1/patients/{patient_id}/allergies/{allergy['id']}/annul",
        headers=headers,
        json={"reason": ""},
    )
    assert missing_reason.status_code == 422

    annulled = await client.post(
        f"/api/v1/patients/{patient_id}/allergies/{allergy['id']}/annul",
        headers=headers,
        json={"reason": "Registrada por error"},
    )
    assert annulled.status_code == 200
    assert annulled.json()["is_active"] is False

    alerts = await client.get(f"/api/v1/patients/{patient_id}/alerts", headers=headers)
    assert alerts.json() == []


async def test_medication_triggers_keyword_alert(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    await client.post(
        f"/api/v1/patients/{patient_id}/medications",
        headers=headers,
        json={"encounter_id": encounter_id, "name": "Warfarina", "dose": "5mg"},
    )

    alerts = await client.get(f"/api/v1/patients/{patient_id}/alerts", headers=headers)
    assert any("anticoagulantes" in a for a in alerts.json())


async def test_history_triggers_keyword_alert(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    await client.post(
        f"/api/v1/patients/{patient_id}/history",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "category": "personal_patologico",
            "text": "Diagnosticada con diabetes hace 10 anos",
        },
    )

    alerts = await client.get(f"/api/v1/patients/{patient_id}/alerts", headers=headers)
    assert "Paciente con diabetes" in alerts.json()


async def test_create_history_rejects_a_category_not_in_the_clinic_catalog(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """B1 (Parte B, Fase 12.2): 'Categorias de antecedentes' ya no es un Literal
    fijo, sino el catalogo administrable de la sucursal."""
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/history",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "category": "no_existe",
            "text": "Antecedente con categoria invalida",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_HISTORY_CATEGORY"


async def test_a_new_alert_keyword_from_the_catalog_triggers_immediately(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """'Palabras clave de alerta' tambien es catalogo administrable (B1): un
    administrador agrega una palabra nueva y, sin tocar codigo, el expediente la
    detecta de inmediato."""
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    await make_user(email="admin@example.com", role_code="admin_clinica")
    admin_token = await _login(client, "admin@example.com")
    create_response = await client.post(
        "/api/v1/catalogs/condition_alert_keyword",
        headers=_headers(admin_token, clinic.id),
        json={
            "code": "asma",
            "name": "asma",
            "extra": {"alert_label": "Paciente con asma"},
        },
    )
    assert create_response.status_code == 201, create_response.text

    await client.post(
        f"/api/v1/patients/{patient_id}/history",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "category": "personal_patologico",
            "text": "Paciente con asma diagnosticada en la infancia",
        },
    )

    alerts = await client.get(f"/api/v1/patients/{patient_id}/alerts", headers=headers)
    assert "Paciente con asma" in alerts.json()


async def test_patient_summary_includes_derived_alerts(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    await client.post(
        f"/api/v1/patients/{patient_id}/allergies",
        headers=headers,
        json={"encounter_id": encounter_id, "substance": "Sulfas", "severity": "severa"},
    )

    summary = await client.get(f"/api/v1/patients/{patient_id}/summary", headers=headers)
    assert summary.status_code == 200
    assert "Alergia severa: Sulfas" in summary.json()["alerts"]


async def test_write_denied_for_role_without_records_write(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    await make_user(email="recepcion@example.com", role_code="recepcion")
    recepcion_token = await _login(client, "recepcion@example.com")

    response = await client.post(
        f"/api/v1/patients/{patient_id}/allergies",
        headers=_headers(recepcion_token, clinic.id),
        json={"encounter_id": encounter_id, "substance": "Penicilina", "severity": "leve"},
    )
    assert response.status_code == 403


async def test_vital_signs_create_and_list(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/vital-signs",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "bp_systolic": 120,
            "bp_diastolic": 80,
            "heart_rate": 72,
        },
    )
    assert created.status_code == 201

    listed = await client.get(f"/api/v1/patients/{patient_id}/vital-signs", headers=headers)
    assert len(listed.json()) == 1
    assert listed.json()[0]["bp_systolic"] == 120
