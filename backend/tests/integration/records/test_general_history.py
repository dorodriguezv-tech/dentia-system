"""Fase A (rediseno del expediente, docs/clinica): pruebas de integracion de
los endpoints nuevos de la Historia Clinica General (heredofamiliares,
antecedentes personales patologicos/no patologicos, aparatos y sistemas,
signos vitales extendidos y el PDF completo)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patients.schemas import PatientCreateRequest
from app.modules.patients.service import create_patient


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _headers(token: str, clinic_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic_id)}


async def _setup(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> tuple[dict, str, str]:
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
    encounter = await client.post(
        "/api/v1/encounters", headers=headers, json={"patient_id": str(patient.id)}
    )
    return headers, str(patient.id), encounter.json()["id"]


async def test_family_history_create_list_and_annul(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/general-history/family",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "relationship_code": "padre",
            "status": "fallecido",
            "conditions": {"diabetes_mellitus": True, "cancer": False},
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["relationship_code"] == "padre"

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/general-history/family", headers=headers
    )
    assert len(listed.json()) == 1

    item_id = created.json()["id"]
    annulled = await client.post(
        f"/api/v1/patients/{patient_id}/general-history/family/{item_id}/annul",
        headers=headers,
        json={"reason": "Capturado por error"},
    )
    assert annulled.status_code == 200
    assert annulled.json()["is_active"] is False


async def test_family_history_rejects_unknown_relationship_code(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/general-history/family",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "relationship_code": "no_existe",
            "status": "en_vida",
            "conditions": {},
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_FAMILY_RELATIONSHIP"


async def test_family_history_rejects_unknown_condition_code(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/general-history/family",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "relationship_code": "padre",
            "status": "en_vida",
            "conditions": {"condicion_inventada": True},
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_FAMILY_CONDITION"


async def test_pathological_history_create_triggers_alert_and_can_be_annulled(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/general-history/pathological",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "dolor_masticar": True,
            "sangrado_encias": "algunas_veces",
            "diseases": {"diabetes": {"present": True, "evolution": "10 anos"}},
        },
    )
    assert created.status_code == 201, created.text

    alerts = await client.get(f"/api/v1/patients/{patient_id}/alerts", headers=headers)
    assert "Paciente con diabetes" in alerts.json()

    item_id = created.json()["id"]
    annulled = await client.post(
        f"/api/v1/patients/{patient_id}/general-history/pathological/{item_id}/annul",
        headers=headers,
        json={"reason": "Correccion"},
    )
    assert annulled.status_code == 200

    alerts_after = await client.get(f"/api/v1/patients/{patient_id}/alerts", headers=headers)
    assert "Paciente con diabetes" not in alerts_after.json()


async def test_pathological_history_rejects_unknown_disease_code(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/general-history/pathological",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "diseases": {"enfermedad_inventada": {"present": True}},
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_PATHOLOGICAL_CONDITION"


async def test_non_pathological_history_create_and_list(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/general-history/non-pathological",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "comidas_dia": 3,
            "calidad_alimentacion": "buena",
            "cepillados_dia": 2,
            "hilo_dental": True,
            "estado_civil": "soltero",
            "derechohabiencia": "civil",
            "servicios_basicos": {"agua": {"has": True}},
            "adicciones": {"tabaco": {"has": False}},
        },
    )
    assert created.status_code == 201, created.text

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/general-history/non-pathological", headers=headers
    )
    assert len(listed.json()) == 1
    assert listed.json()[0]["estado_civil"] == "soltero"


async def test_systems_review_create_rejects_unknown_finding_code(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/general-history/systems-review",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "hematologico": {"padecimiento_inventado": {"present": True}},
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_SYSTEMS_REVIEW_FINDING"


async def test_systems_review_create_list_and_annul(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/general-history/systems-review",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "cardiovascular": {"arritmias": {"present": True, "evolution": "desde los 20"}},
            "reproductor_femenino": {"embarazos": 2, "partos": 1},
        },
    )
    assert created.status_code == 201, created.text

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/general-history/systems-review", headers=headers
    )
    assert len(listed.json()) == 1

    item_id = created.json()["id"]
    annulled = await client.post(
        f"/api/v1/patients/{patient_id}/general-history/systems-review/{item_id}/annul",
        headers=headers,
        json={"reason": "Correccion"},
    )
    assert annulled.status_code == 200
    assert annulled.json()["is_active"] is False


async def test_vital_signs_with_extended_fields_computes_bmi(
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
            "height_m": 1.75,
            "weight_kg": 70,
            "spo2": 98,
            "glucose_index": 95,
            "glucose_timing": "preprandial",
            "patient_attitude": "cooperador",
            "asa_classification": "ASA I",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["body_mass_index"] == 22.9
    assert created.json()["patient_attitude"] == "cooperador"

    listed = await client.get(f"/api/v1/patients/{patient_id}/vital-signs", headers=headers)
    assert listed.json()[0]["body_mass_index"] == 22.9


async def test_general_history_write_denied_for_role_without_records_write(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    await make_user(email="recepcion@example.com", role_code="recepcion")
    recepcion_token = await _login(client, "recepcion@example.com")

    response = await client.post(
        f"/api/v1/patients/{patient_id}/general-history/family",
        headers=_headers(recepcion_token, clinic.id),
        json={
            "encounter_id": encounter_id,
            "relationship_code": "padre",
            "status": "en_vida",
            "conditions": {},
        },
    )
    assert response.status_code == 403


async def test_general_history_pdf_renders(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    await client.post(
        f"/api/v1/patients/{patient_id}/general-history/family",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "relationship_code": "padre",
            "status": "fallecido",
            "conditions": {"diabetes_mellitus": True},
        },
    )
    await client.post(
        f"/api/v1/patients/{patient_id}/allergies",
        headers=headers,
        json={"encounter_id": encounter_id, "substance": "Penicilina", "severity": "leve"},
    )

    response = await client.get(
        f"/api/v1/patients/{patient_id}/general-history/pdf", headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
