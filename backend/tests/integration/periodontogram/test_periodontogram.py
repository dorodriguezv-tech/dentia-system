"""Fase G (rediseno del expediente, docs/clinica -- ultimo slice del
proyecto): pruebas de integracion de los endpoints del Periodontograma
completo (sondeo, medicion por pieza, indices, oclusion, observaciones y el
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
    await make_user(email="perio@example.com", role_code="odontologo")
    token = await _login(client, "perio@example.com")
    headers = _headers(token, clinic.id)
    patient = await create_patient(
        db_session,
        clinic_id=clinic.id,
        data=PatientCreateRequest(
            first_name="Marcela", last_name_paternal="Ibarra", date_of_birth="1988-04-15"
        ),
        actor_id=None,
    )
    encounter = await client.post(
        "/api/v1/encounters", headers=headers, json={"patient_id": str(patient.id)}
    )
    return headers, str(patient.id), encounter.json()["id"]


# --------------------------------------------------------------------------------
# 1. Sondeo periodontal.
# --------------------------------------------------------------------------------


async def test_probing_site_create_list_and_annul(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/probing-sites",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tooth_fdi": "16",
            "site": "mesiovestibular",
            "probing_depth_mm": 3,
            "recession_mm": 1,
            "bleeding_on_probing": True,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["probing_depth_mm"] == 3
    # CAL calculado al vuelo (no persistido), nunca desincronizado.
    assert created.json()["clinical_attachment_level_mm"] == 4

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/probing-sites", headers=headers
    )
    assert len(listed.json()) == 1
    assert listed.json()[0]["clinical_attachment_level_mm"] == 4

    item_id = created.json()["id"]
    annulled = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/probing-sites/{item_id}/annul",
        headers=headers,
        json={"reason": "Capturado por error"},
    )
    assert annulled.status_code == 200
    assert annulled.json()["is_active"] is False


def test_probing_site_schema_allows_negative_recession() -> None:
    # Recesion negativa (cobertura gingival) reduce el CAL -- se prueba el
    # schema directamente, sin red (no necesita los fixtures de integracion).
    from app.modules.periodontogram.schemas import PeriodontalProbingSiteCreateRequest

    payload = PeriodontalProbingSiteCreateRequest(
        encounter_id="11111111-1111-1111-1111-111111111111",
        tooth_fdi="16",
        site="vestibular",
        probing_depth_mm=2,
        recession_mm=-3,
    )
    assert payload.recession_mm == -3


async def test_probing_site_rejects_invalid_tooth(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/probing-sites",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tooth_fdi": "55",
            "site": "vestibular",
            "probing_depth_mm": 2,
            "recession_mm": 0,
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_TOOTH"


async def test_probing_site_rejects_depth_out_of_range(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/probing-sites",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tooth_fdi": "16",
            "site": "vestibular",
            "probing_depth_mm": 99,
            "recession_mm": 0,
        },
    )
    assert response.status_code == 422


async def test_probing_site_re_annotating_same_tooth_and_site_annuls_previous(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    first = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/probing-sites",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tooth_fdi": "16",
            "site": "vestibular",
            "probing_depth_mm": 2,
            "recession_mm": 0,
        },
    )
    assert first.status_code == 201, first.text
    first_id = first.json()["id"]

    second = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/probing-sites",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tooth_fdi": "16",
            "site": "vestibular",
            "probing_depth_mm": 5,
            "recession_mm": 2,
        },
    )
    assert second.status_code == 201, second.text

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/probing-sites", headers=headers
    )
    items = {item["id"]: item for item in listed.json()}
    assert items[first_id]["is_active"] is False
    active_items = [item for item in listed.json() if item["is_active"]]
    assert len(active_items) == 1
    assert active_items[0]["probing_depth_mm"] == 5


async def test_probing_site_same_tooth_different_site_both_stay_active(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    for site in ("vestibular", "lingual"):
        created = await client.post(
            f"/api/v1/patients/{patient_id}/periodontogram/probing-sites",
            headers=headers,
            json={
                "encounter_id": encounter_id,
                "tooth_fdi": "16",
                "site": site,
                "probing_depth_mm": 2,
                "recession_mm": 0,
            },
        )
        assert created.status_code == 201, created.text

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/probing-sites", headers=headers
    )
    active_items = [item for item in listed.json() if item["is_active"]]
    assert len(active_items) == 2


# --------------------------------------------------------------------------------
# 2. Medicion por pieza.
# --------------------------------------------------------------------------------


async def test_tooth_measurement_create_list_and_annul(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/tooth-measurements",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tooth_fdi": "36",
            "mobility_grade": 2,
            "furcation_grade": 1,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["mobility_grade"] == 2

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/tooth-measurements", headers=headers
    )
    assert len(listed.json()) == 1

    item_id = created.json()["id"]
    annulled = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/tooth-measurements/{item_id}/annul",
        headers=headers,
        json={"reason": "Correccion"},
    )
    assert annulled.status_code == 200
    assert annulled.json()["is_active"] is False


async def test_tooth_measurement_re_annotating_same_tooth_annuls_previous(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    first = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/tooth-measurements",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "36", "mobility_grade": 1},
    )
    assert first.status_code == 201, first.text
    first_id = first.json()["id"]

    second = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/tooth-measurements",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "36", "mobility_grade": 3},
    )
    assert second.status_code == 201, second.text

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/tooth-measurements", headers=headers
    )
    items = {item["id"]: item for item in listed.json()}
    assert items[first_id]["is_active"] is False
    active_items = [item for item in listed.json() if item["is_active"]]
    assert len(active_items) == 1
    assert active_items[0]["mobility_grade"] == 3


async def test_tooth_measurement_rejects_invalid_tooth_and_out_of_range_grade(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    invalid_tooth = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/tooth-measurements",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "55", "mobility_grade": 1},
    )
    assert invalid_tooth.status_code == 422
    assert invalid_tooth.json()["code"] == "INVALID_TOOTH"

    invalid_grade = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/tooth-measurements",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "16", "furcation_grade": 9},
    )
    assert invalid_grade.status_code == 422


# --------------------------------------------------------------------------------
# 3. Indices de placa dentobacteriana y gingival.
# --------------------------------------------------------------------------------


async def test_index_entry_create_list_filter_and_annul(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    placa = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/index-entries",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tooth_fdi": "16",
            "index_type": "placa",
            "surface": "vestibular",
            "grade": 2,
        },
    )
    assert placa.status_code == 201, placa.text

    gingival = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/index-entries",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tooth_fdi": "16",
            "index_type": "gingival",
            "surface": "vestibular",
            "grade": 1,
        },
    )
    assert gingival.status_code == 201, gingival.text

    listed_all = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/index-entries", headers=headers
    )
    assert len(listed_all.json()) == 2

    listed_placa = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/index-entries?index_type=placa",
        headers=headers,
    )
    assert len(listed_placa.json()) == 1
    assert listed_placa.json()[0]["index_type"] == "placa"

    item_id = placa.json()["id"]
    annulled = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/index-entries/{item_id}/annul",
        headers=headers,
        json={"reason": "Correccion"},
    )
    assert annulled.status_code == 200
    assert annulled.json()["is_active"] is False


async def test_index_entry_re_annotating_same_tooth_type_and_surface_annuls_previous(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    first = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/index-entries",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tooth_fdi": "16",
            "index_type": "placa",
            "surface": "vestibular",
            "grade": 1,
        },
    )
    assert first.status_code == 201, first.text
    first_id = first.json()["id"]

    second = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/index-entries",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tooth_fdi": "16",
            "index_type": "placa",
            "surface": "vestibular",
            "grade": 3,
        },
    )
    assert second.status_code == 201, second.text

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/index-entries", headers=headers
    )
    items = {item["id"]: item for item in listed.json()}
    assert items[first_id]["is_active"] is False
    active_items = [item for item in listed.json() if item["is_active"]]
    assert len(active_items) == 1
    assert active_items[0]["grade"] == 3


async def test_indices_summary_computes_plaque_and_gingival_totals(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    # Placa: 16-vestibular=2, 16-lingual=0 -> 1/2 caras con placa = 0.5.
    for surface, grade in (("vestibular", 2), ("lingual", 0)):
        response = await client.post(
            f"/api/v1/patients/{patient_id}/periodontogram/index-entries",
            headers=headers,
            json={
                "encounter_id": encounter_id,
                "tooth_fdi": "16",
                "index_type": "placa",
                "surface": surface,
                "grade": grade,
            },
        )
        assert response.status_code == 201, response.text

    # Gingival: 16-vestibular=2, 16-lingual=0 -> media = 1.0.
    for surface, grade in (("vestibular", 2), ("lingual", 0)):
        response = await client.post(
            f"/api/v1/patients/{patient_id}/periodontogram/index-entries",
            headers=headers,
            json={
                "encounter_id": encounter_id,
                "tooth_fdi": "16",
                "index_type": "gingival",
                "surface": surface,
                "grade": grade,
            },
        )
        assert response.status_code == 201, response.text

    summary = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/indices-summary", headers=headers
    )
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["encounter_id"] == encounter_id
    assert body["placa"]["numero_caras_totales"] == 2
    assert body["placa"]["numero_caras_pigmentadas"] == 1
    assert body["placa"]["indice_placa_dentobacteriana"] == 0.5
    assert body["gingival"]["numero_sitios_totales"] == 2
    assert body["gingival"]["indice_gingival_total"] == 1.0

    # Explicito por encounter_id da el mismo resultado.
    summary_explicit = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/indices-summary"
        f"?encounter_id={encounter_id}",
        headers=headers,
    )
    assert summary_explicit.json() == body


async def test_indices_summary_with_no_data_returns_none_not_zero(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, _encounter_id = await _setup(client, make_user, clinic, db_session)

    summary = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/indices-summary", headers=headers
    )
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["encounter_id"] is None
    assert body["placa"]["indice_placa_dentobacteriana"] is None
    assert body["gingival"]["indice_gingival_total"] is None


# --------------------------------------------------------------------------------
# 4. Tablas de oclusion.
# --------------------------------------------------------------------------------


async def test_occlusal_contact_create_list_and_annul(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/occlusal-contacts",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "16", "movement": "centrica"},
    )
    assert created.status_code == 201, created.text

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/occlusal-contacts", headers=headers
    )
    assert len(listed.json()) == 1

    item_id = created.json()["id"]
    annulled = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/occlusal-contacts/{item_id}/annul",
        headers=headers,
        json={"reason": "Se desmarca el contacto"},
    )
    assert annulled.status_code == 200
    assert annulled.json()["is_active"] is False


async def test_occlusal_contact_marking_same_tooth_and_movement_twice_is_idempotent(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    first = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/occlusal-contacts",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "16", "movement": "protrusion"},
    )
    assert first.status_code == 201, first.text

    second = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/occlusal-contacts",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "16", "movement": "protrusion"},
    )
    assert second.status_code == 201, second.text
    # No se crea un duplicado: devuelve la misma fila activa existente.
    assert second.json()["id"] == first.json()["id"]

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/occlusal-contacts", headers=headers
    )
    assert len(listed.json()) == 1


async def test_occlusal_contact_allows_several_teeth_per_movement(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    for tooth in ("16", "17", "26"):
        response = await client.post(
            f"/api/v1/patients/{patient_id}/periodontogram/occlusal-contacts",
            headers=headers,
            json={"encounter_id": encounter_id, "tooth_fdi": tooth, "movement": "centrica"},
        )
        assert response.status_code == 201, response.text

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/occlusal-contacts", headers=headers
    )
    assert len(listed.json()) == 3


# --------------------------------------------------------------------------------
# 5. Observaciones.
# --------------------------------------------------------------------------------


async def test_observation_create_list_and_annul(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/observations",
        headers=headers,
        json={"encounter_id": encounter_id, "observaciones": "Paciente con higiene regular."},
    )
    assert created.status_code == 201, created.text

    listed = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/observations", headers=headers
    )
    assert len(listed.json()) == 1

    item_id = created.json()["id"]
    annulled = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/observations/{item_id}/annul",
        headers=headers,
        json={"reason": "Correccion"},
    )
    assert annulled.status_code == 200
    assert annulled.json()["is_active"] is False


# --------------------------------------------------------------------------------
# Permisos y PDF.
# --------------------------------------------------------------------------------


async def test_periodontogram_write_denied_for_role_without_records_write(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    await make_user(email="recepcion_perio@example.com", role_code="recepcion")
    recepcion_token = await _login(client, "recepcion_perio@example.com")

    response = await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/observations",
        headers=_headers(recepcion_token, clinic.id),
        json={"encounter_id": encounter_id},
    )
    assert response.status_code == 403


async def test_periodontogram_pdf_renders(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/probing-sites",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tooth_fdi": "16",
            "site": "mesiovestibular",
            "probing_depth_mm": 3,
            "recession_mm": 1,
            "bleeding_on_probing": True,
        },
    )
    await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/tooth-measurements",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "16", "mobility_grade": 1},
    )
    await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/index-entries",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tooth_fdi": "16",
            "index_type": "placa",
            "surface": "vestibular",
            "grade": 1,
        },
    )
    await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/occlusal-contacts",
        headers=headers,
        json={"encounter_id": encounter_id, "tooth_fdi": "16", "movement": "centrica"},
    )
    await client.post(
        f"/api/v1/patients/{patient_id}/periodontogram/observations",
        headers=headers,
        json={"encounter_id": encounter_id, "observaciones": "Observacion de prueba."},
    )

    response = await client.get(
        f"/api/v1/patients/{patient_id}/periodontogram/pdf", headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
