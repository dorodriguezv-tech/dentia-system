"""Fase F (rediseno del expediente, docs/clinica): pruebas de integracion de
los endpoints de la Historia Clinica de Endodoncia (las 7 secciones + el
PDF)."""

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
    await make_user(email="endo@example.com", role_code="odontologo")
    token = await _login(client, "endo@example.com")
    headers = _headers(token, clinic.id)
    patient = await create_patient(
        db_session,
        clinic_id=clinic.id,
        data=PatientCreateRequest(
            first_name="Luis", last_name_paternal="Fernandez", date_of_birth="1990-02-10"
        ),
        actor_id=None,
    )
    encounter = await client.post(
        "/api/v1/encounters", headers=headers, json={"patient_id": str(patient.id)}
    )
    return headers, str(patient.id), encounter.json()["id"]


async def test_interrogation_create_list_and_annul(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/interrogation",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "antecedentes": {"caries": True, "tratamiento_conductos": False},
            "dolor": {"localizado": True, "espontaneo": True},
            "estimulo": {"frio": True},
            "examen_intrabucal": {"exposicion_pulpar": True},
            "examen_extrabucal": {"inflamacion": False},
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["antecedentes"]["caries"] is True
    assert created.json()["dolor"]["espontaneo"] is True

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/endodontic-history/interrogation", headers=headers
    )
    assert len(listed.json()) == 1

    item_id = created.json()["id"]
    annulled = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/interrogation/{item_id}/annul",
        headers=headers,
        json={"reason": "Capturado por error"},
    )
    assert annulled.status_code == 200
    assert annulled.json()["is_active"] is False


async def test_interrogation_rejects_unknown_checklist_key(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/interrogation",
        headers=headers,
        json={"encounter_id": encounter_id, "antecedentes": {"no_existe": True}},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_CHECKLIST_KEY"


async def test_pulp_sensitivity_test_create_allows_several_rows_per_encounter(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    for payload in (
        {"encounter_id": encounter_id, "frio": True, "fugaz": True, "diente_testigo_od": "11"},
        {"encounter_id": encounter_id, "calor": True, "persistente": True},
    ):
        created = await client.post(
            f"/api/v1/patients/{patient_id}/endodontic-history/pulp-sensitivity-test",
            headers=headers,
            json=payload,
        )
        assert created.status_code == 201, created.text

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/endodontic-history/pulp-sensitivity-test", headers=headers
    )
    assert len(listed.json()) == 2


async def test_periodontal_test_create_and_movilidad_grado_only_if_positiva(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/periodontal-test",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "percusion_horizontal": {"fugaz": True},
            "movilidad_horizontal": "positiva",
            "movilidad_horizontal_grado": "II",
            "palpacion": "negativa",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["movilidad_horizontal_grado"] == "II"

    rejected = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/periodontal-test",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "movilidad_vertical": "negativa",
            "movilidad_vertical_grado": "I",
        },
    )
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "INVALID_MOVILIDAD_GRADO"


async def test_periodontal_test_rejects_unknown_percusion_key(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/periodontal-test",
        headers=headers,
        json={"encounter_id": encounter_id, "percusion_vertical": {"no_existe": True}},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_CHECKLIST_KEY"


async def test_radiographic_interpretation_create_and_rejects_unknown_key(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/radiographic-interpretation",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "camara": {"calcificada": True},
            "conducto": {"obturado": True},
            "periodonto": {"resorcion_apical": True, "otro": True},
            "periodonto_otro_detalle": "Lesion en apice",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["periodonto_otro_detalle"] == "Lesion en apice"

    rejected = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/radiographic-interpretation",
        headers=headers,
        json={"encounter_id": encounter_id, "conducto": {"no_existe": True}},
    )
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "INVALID_CHECKLIST_KEY"


async def test_diagnosis_treatment_create_with_single_diagnoses_and_multiselect_treatment(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/diagnosis-treatment",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "diagnostico_pulpar": "pulpitis_irreversible",
            "diagnostico_periapical": "periodontitis_aguda",
            "tratamiento": {"biopulpectomia": True, "perno_munon": True},
            "cirugia": {"apicectomia": True},
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["diagnostico_pulpar"] == "pulpitis_irreversible"
    assert created.json()["tratamiento"]["biopulpectomia"] is True

    rejected = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/diagnosis-treatment",
        headers=headers,
        json={"encounter_id": encounter_id, "diagnostico_pulpar": "no_existe"},
    )
    assert rejected.status_code == 422


async def test_tooth_diagnosis_code_create_rejects_invalid_tooth_and_invalid_code(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    invalid_tooth = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/tooth-diagnosis-code",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "55", "kind": "diagnostico", "code": 1},
    )
    assert invalid_tooth.status_code == 422
    assert invalid_tooth.json()["code"] == "INVALID_TOOTH"

    invalid_code = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/tooth-diagnosis-code",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "16", "kind": "diagnostico", "code": 99},
    )
    assert invalid_code.status_code == 422


async def test_tooth_diagnosis_code_re_annotating_same_tooth_same_kind_annuls_previous(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    first = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/tooth-diagnosis-code",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "16", "kind": "diagnostico", "code": 1},
    )
    assert first.status_code == 201, first.text
    first_id = first.json()["id"]

    second = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/tooth-diagnosis-code",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "16", "kind": "diagnostico", "code": 12},
    )
    assert second.status_code == 201, second.text

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/endodontic-history/tooth-diagnosis-code", headers=headers
    )
    items = {item["id"]: item for item in listed.json()}
    assert items[first_id]["is_active"] is False
    active_items = [item for item in listed.json() if item["is_active"]]
    assert len(active_items) == 1
    assert active_items[0]["code"] == 12


async def test_tooth_diagnosis_code_diagnostico_and_evolucion_coexist_independently(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    diagnostico = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/tooth-diagnosis-code",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "26", "kind": "diagnostico", "code": 1},
    )
    assert diagnostico.status_code == 201, diagnostico.text

    evolucion = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/tooth-diagnosis-code",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "26", "kind": "evolucion", "code": 12},
    )
    assert evolucion.status_code == 201, evolucion.text

    listed_diagnostico = await client.get(
        f"/api/v1/patients/{patient_id}/endodontic-history/tooth-diagnosis-code"
        "?kind=diagnostico",
        headers=headers,
    )
    assert len(listed_diagnostico.json()) == 1
    assert listed_diagnostico.json()[0]["is_active"] is True

    listed_evolucion = await client.get(
        f"/api/v1/patients/{patient_id}/endodontic-history/tooth-diagnosis-code?kind=evolucion",
        headers=headers,
    )
    assert len(listed_evolucion.json()) == 1
    assert listed_evolucion.json()[0]["is_active"] is True


async def test_working_length_create_with_canal_measurements_and_rejects_unknown_canal_key(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/working-length",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tooth_fdi": "36",
            "canal_measurements": {
                "mesial": {"aparente_rx": "20mm", "real_localizador": "19mm", "relacion": "1:1"},
                "distal": {"aparente_rx": "21mm"},
            },
            "tecnica_instrumentacion": "Rotatoria",
            "tecnica_obturacion": "Condensacion lateral",
            "fecha_inicio": "10/10/2026",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["canal_measurements"]["mesial"]["aparente_rx"] == "20mm"

    rejected = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/working-length",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "canal_measurements": {"no_existe": {"aparente_rx": "1mm"}},
        },
    )
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "INVALID_CHECKLIST_KEY"


async def test_working_length_rejects_invalid_tooth(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/working-length",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "55"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_TOOTH"


async def test_endodontic_history_write_denied_for_role_without_records_write(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    await make_user(email="recepcion_endo@example.com", role_code="recepcion")
    recepcion_token = await _login(client, "recepcion_endo@example.com")

    response = await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/interrogation",
        headers=_headers(recepcion_token, clinic.id),
        json={"encounter_id": encounter_id},
    )
    assert response.status_code == 403


async def test_endodontic_history_pdf_renders(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/interrogation",
        headers=headers,
        json={"encounter_id": encounter_id, "dolor": {"espontaneo": True}},
    )
    await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/tooth-diagnosis-code",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "16", "kind": "diagnostico", "code": 1},
    )
    await client.post(
        f"/api/v1/patients/{patient_id}/endodontic-history/working-length",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tooth_fdi": "16",
            "canal_measurements": {"unico": {"aparente_rx": "20mm"}},
        },
    )

    response = await client.get(
        f"/api/v1/patients/{patient_id}/endodontic-history/pdf", headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
