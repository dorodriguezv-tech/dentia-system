"""Fase E (rediseno del expediente, docs/clinica): pruebas de integracion de
los endpoints de la Historia Clinica Pediatrica (las 6 secciones + el PDF)."""

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
            first_name="Sofia", last_name_paternal="Ramirez", date_of_birth="2019-05-20"
        ),
        actor_id=None,
    )
    encounter = await client.post(
        "/api/v1/encounters", headers=headers, json={"patient_id": str(patient.id)}
    )
    return headers, str(patient.id), encounter.json()["id"]


async def test_perinatal_history_create_list_and_annul(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/perinatal-history",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tomo_medicamentos_embarazo": True,
            "tomo_medicamentos_embarazo_cuales": "Acido folico",
            "vacunas_completas": True,
            "fecha_ultima_visita_dentista": "Hace 6 meses",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["tomo_medicamentos_embarazo"] is True

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/pediatric-history/perinatal-history", headers=headers
    )
    assert len(listed.json()) == 1

    item_id = created.json()["id"]
    annulled = await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/perinatal-history/{item_id}/annul",
        headers=headers,
        json={"reason": "Capturado por error"},
    )
    assert annulled.status_code == 200
    assert annulled.json()["is_active"] is False


async def test_oral_habits_create_and_list(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/oral-habits",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "cepilla_despues_alimento": True,
            "sangran_encias_sin_cepillar": False,
            "bruxismo_nocturno": True,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["bruxismo_nocturno"] is True

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/pediatric-history/oral-habits", headers=headers
    )
    assert len(listed.json()) == 1


async def test_behavior_maturity_create_and_rejects_unknown_character(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/behavior-maturity",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "toma_biberon_actualmente": True,
            "edad_dejo_biberon": "3 anos",
            "caracter": "inquieto",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["caracter"] == "inquieto"
    assert created.json()["edad_dejo_biberon"] == "3 anos"

    rejected = await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/behavior-maturity",
        headers=headers,
        json={"encounter_id": encounter_id, "caracter": "no_existe"},
    )
    assert rejected.status_code == 400
    assert rejected.json()["code"] == "INVALID_PEDIATRIC_CHARACTER"


async def test_occlusion_create_with_numeric_fields_and_rejects_unknown_terminal_plane(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/occlusion",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "planos_terminales_izq": "recto",
            "planos_terminales_der": "mesial",
            "overjet_mm": 2.5,
            "overbite_mm": -1.0,
            "mordida_cruzada": True,
            "linea_media": "desviada_izquierda",
            "clasificacion_angle": "II",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["overbite_mm"] == -1.0
    assert created.json()["clasificacion_angle"] == "II"

    rejected = await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/occlusion",
        headers=headers,
        json={"encounter_id": encounter_id, "planos_terminales_izq": "no_existe"},
    )
    assert rejected.status_code == 400
    assert rejected.json()["code"] == "INVALID_TERMINAL_PLANE"


async def test_occlusion_rejects_overjet_out_of_range(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/occlusion",
        headers=headers,
        json={"encounter_id": encounter_id, "overjet_mm": 999},
    )
    assert response.status_code == 422


async def test_eruption_dentition_create_and_list(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/eruption-dentition",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "secuencia_normal": True,
            "perdida_prematura": False,
            "edad_dental": "Acorde a la edad cronologica",
        },
    )
    assert created.status_code == 201, created.text

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/pediatric-history/eruption-dentition", headers=headers
    )
    assert len(listed.json()) == 1


async def test_tooth_annotation_create_rejects_invalid_tooth_and_unknown_anomaly(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    invalid_tooth = await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/tooth-annotation",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "99", "anomaly_code": "hipoplasia"},
    )
    assert invalid_tooth.status_code == 422
    assert invalid_tooth.json()["code"] == "INVALID_TOOTH"

    unknown_anomaly = await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/tooth-annotation",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "55", "anomaly_code": "no_existe"},
    )
    assert unknown_anomaly.status_code == 400
    assert unknown_anomaly.json()["code"] == "INVALID_PEDIATRIC_TOOTH_ANOMALY"


async def test_tooth_annotation_accepts_temporary_tooth_with_ausente_congenito(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/tooth-annotation",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "55", "anomaly_code": "ausente_congenito"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["anomaly_code"] == "ausente_congenito"

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/pediatric-history/tooth-annotation", headers=headers
    )
    assert len(listed.json()) == 1


async def test_tooth_annotation_with_hipoplasia_detail_free_text(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/tooth-annotation",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tooth_fdi": "16",
            "anomaly_code": "hipoplasia",
            "hipoplasia_detail": "1/3 incisal",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["hipoplasia_detail"] == "1/3 incisal"


async def test_tooth_annotation_re_annotating_same_tooth_same_encounter_annuls_previous(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    # Decision documentada (models.py/PENDIENTES_CLINICOS.md): re-anotar la
    # MISMA pieza en el MISMO encounter anula automaticamente la anotacion
    # anterior de esa pieza -- solo una vigente a la vez.
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    first = await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/tooth-annotation",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "55", "anomaly_code": "movilidad"},
    )
    assert first.status_code == 201, first.text
    first_id = first.json()["id"]

    second = await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/tooth-annotation",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "55", "anomaly_code": "ausente_adquirida"},
    )
    assert second.status_code == 201, second.text

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/pediatric-history/tooth-annotation", headers=headers
    )
    items = {item["id"]: item for item in listed.json()}
    assert items[first_id]["is_active"] is False
    active_items = [item for item in listed.json() if item["is_active"]]
    assert len(active_items) == 1
    assert active_items[0]["anomaly_code"] == "ausente_adquirida"


async def test_pediatric_history_write_denied_for_role_without_records_write(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    await make_user(email="recepcion@example.com", role_code="recepcion")
    recepcion_token = await _login(client, "recepcion@example.com")

    response = await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/oral-habits",
        headers=_headers(recepcion_token, clinic.id),
        json={"encounter_id": encounter_id},
    )
    assert response.status_code == 403


async def test_pediatric_history_pdf_renders(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/oral-habits",
        headers=headers,
        json={"encounter_id": encounter_id, "cepilla_despues_alimento": True},
    )
    await client.post(
        f"/api/v1/patients/{patient_id}/pediatric-history/tooth-annotation",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "55", "anomaly_code": "ausente_congenito"},
    )

    response = await client.get(
        f"/api/v1/patients/{patient_id}/pediatric-history/pdf", headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
