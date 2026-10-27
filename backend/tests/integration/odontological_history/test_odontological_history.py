"""Fase C (rediseno del expediente, docs/clinica): pruebas de integracion de
los endpoints nuevos de la Historia Clinica Odontologica (las 8 secciones +
el PDF)."""

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
            first_name="Maria", last_name_paternal="Lopez", date_of_birth="1988-03-12"
        ),
        actor_id=None,
    )
    encounter = await client.post(
        "/api/v1/encounters", headers=headers, json={"patient_id": str(patient.id)}
    )
    return headers, str(patient.id), encounter.json()["id"]


async def test_odontological_exam_create_list_and_annul(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/exam",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "skull_type": "mesocefalo",
            "facial_biotype": "mesofacial",
            "apertura_conservada_mm": 40,
            "chasquidos_derecho": True,
            "lengua": "Sin alteraciones",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["skull_type"] == "mesocefalo"
    assert created.json()["chasquidos_derecho"] is True

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/odontological-history/exam", headers=headers
    )
    assert len(listed.json()) == 1

    item_id = created.json()["id"]
    annulled = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/exam/{item_id}/annul",
        headers=headers,
        json={"reason": "Capturado por error"},
    )
    assert annulled.status_code == 200
    assert annulled.json()["is_active"] is False


async def test_odontological_exam_rejects_unknown_skull_type(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/exam",
        headers=headers,
        json={"encounter_id": encounter_id, "skull_type": "no_existe"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_SKULL_TYPE"


async def test_periodontal_anamnesis_create_and_list(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/periodontal-anamnesis",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "answers": {
                "sensibilidad_frio": "si",
                "fuma": "no",
                "embarazada": "no_recuerda",
            },
            "cepillado_veces_dia": 2,
            "salud_bucal_autopercibida": "buena",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["answers"]["sensibilidad_frio"] == "si"

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/odontological-history/periodontal-anamnesis",
        headers=headers,
    )
    assert len(listed.json()) == 1


async def test_periodontal_anamnesis_rejects_unknown_question_code(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/periodontal-anamnesis",
        headers=headers,
        json={"encounter_id": encounter_id, "answers": {"pregunta_inventada": "si"}},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_PERIODONTAL_ANAMNESIS_QUESTION"


async def test_periodontal_anamnesis_rejects_invalid_answer_value(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/periodontal-anamnesis",
        headers=headers,
        json={"encounter_id": encounter_id, "answers": {"fuma": "tal_vez"}},
    )
    assert response.status_code == 422


async def test_radiographic_analysis_create_and_rejects_unknown_type(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/radiographic-analysis",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "findings": {
                "perdida_osea_horizontal": {
                    "organos_dentarios": "16, 17",
                    "porcentaje": "30",
                    "alteracion": "Leve",
                }
            },
            "anexos_nota": "Panoramica anexa en imagenologia",
        },
    )
    assert created.status_code == 201, created.text

    rejected = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/radiographic-analysis",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "findings": {"tipo_inventado": {"organos_dentarios": "11"}},
        },
    )
    assert rejected.status_code == 400
    assert rejected.json()["code"] == "INVALID_RADIOGRAPHIC_FINDING_TYPE"


async def test_odontogram_diagnosis_detail_create_and_rejects_invalid_tooth(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/odontogram-diagnosis-detail",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "edentulous_space_available": True,
            "kennedy_sup_class": "I",
            "kennedy_sup_modification": True,
            "fixed_prosthesis_analysis": [{"tooth_fdi": "16", "cr_relation": "1:1.5"}],
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["kennedy_sup_class"] == "I"

    rejected = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/odontogram-diagnosis-detail",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "fixed_prosthesis_analysis": [{"tooth_fdi": "99", "cr_relation": "1:1"}],
        },
    )
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "INVALID_TOOTH"


async def test_parallelometer_analysis_create_and_list(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/parallelometer-analysis",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "entries": [
                {
                    "organo_dental": "16",
                    "caracteristicas": "Retentivo mesial",
                    "plan_tratamiento": "Retenedor circunferencial",
                }
            ],
        },
    )
    assert created.status_code == 201, created.text

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/odontological-history/parallelometer-analysis",
        headers=headers,
    )
    assert len(listed.json()) == 1


async def test_removable_partial_denture_design_create_and_annul(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/removable-partial-denture-design",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "conector_mayor": "Barra palatina",
            "retenedores_directos": "Gancho circunferencial en 16 y 26",
        },
    )
    assert created.status_code == 201, created.text

    item_id = created.json()["id"]
    annulled = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/"
        f"removable-partial-denture-design/{item_id}/annul",
        headers=headers,
        json={"reason": "Correccion"},
    )
    assert annulled.status_code == 200
    assert annulled.json()["is_active"] is False


async def test_tooth_diagnosis_entry_create_and_rejects_invalid_tooth(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/tooth-diagnosis",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "diagnoses": {"16": "Caries oclusal", "26": "Sano"},
            "observaciones": "Revision general",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["diagnoses"]["16"] == "Caries oclusal"

    rejected = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/tooth-diagnosis",
        headers=headers,
        json={"encounter_id": encounter_id, "diagnoses": {"55": "Pieza temporal"}},
    )
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "INVALID_TOOTH"


async def test_tooth_treatment_plan_entry_create_list_and_annul(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/tooth-treatment-plan",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "plans": {"16": "Resina compuesta"},
        },
    )
    assert created.status_code == 201, created.text

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/odontological-history/tooth-treatment-plan",
        headers=headers,
    )
    assert len(listed.json()) == 1

    item_id = created.json()["id"]
    annulled = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/tooth-treatment-plan/"
        f"{item_id}/annul",
        headers=headers,
        json={"reason": "Correccion"},
    )
    assert annulled.status_code == 200
    assert annulled.json()["is_active"] is False


async def test_tooth_treatment_plan_entry_accepts_temporary_tooth(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    # Fase E (Historia Clinica Pediatrica): este mismo endpoint se reutiliza
    # para el plan pediatrico permanente/temporal, asi que debe aceptar
    # tambien piezas temporales (51-85) -- a diferencia de tooth-diagnosis,
    # que las sigue rechazando (ver test de arriba).
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/tooth-treatment-plan",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "plans": {"55": "Pulpotomia", "16": "Resina compuesta"},
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["plans"]["55"] == "Pulpotomia"


async def test_odontological_history_write_denied_for_role_without_records_write(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    await make_user(email="recepcion@example.com", role_code="recepcion")
    recepcion_token = await _login(client, "recepcion@example.com")

    response = await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/exam",
        headers=_headers(recepcion_token, clinic.id),
        json={"encounter_id": encounter_id},
    )
    assert response.status_code == 403


async def test_odontological_history_pdf_renders(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/exam",
        headers=headers,
        json={"encounter_id": encounter_id, "skull_type": "mesocefalo"},
    )
    await client.post(
        f"/api/v1/patients/{patient_id}/odontological-history/tooth-diagnosis",
        headers=headers,
        json={"encounter_id": encounter_id, "diagnoses": {"16": "Caries oclusal"}},
    )

    response = await client.get(
        f"/api/v1/patients/{patient_id}/odontological-history/pdf", headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
