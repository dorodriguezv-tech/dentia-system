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

    catalog_resp = await client.post(
        "/api/v1/procedure-catalog",
        headers=headers,
        json={"code": "resina_oclusal", "name": "Resina oclusal", "default_price": "500.00"},
    )
    assert catalog_resp.status_code == 201, catalog_resp.text

    return headers, str(patient.id), encounter_id


async def _make_plan_with_item(
    client: AsyncClient, headers: dict, patient_id: str, encounter_id: str
):
    plan_resp = await client.post(
        "/api/v1/treatment-plans",
        headers=headers,
        json={"patient_id": patient_id, "encounter_id": encounter_id, "title": "Plan general"},
    )
    assert plan_resp.status_code == 201, plan_resp.text
    plan_id = plan_resp.json()["id"]

    phase_resp = await client.post(
        f"/api/v1/treatment-plans/{plan_id}/phases",
        headers=headers,
        json={"name": "Fase 1", "sort_order": 1, "priority": "alta"},
    )
    assert phase_resp.status_code == 201, phase_resp.text
    phase_id = phase_resp.json()["id"]

    item_resp = await client.post(
        f"/api/v1/treatment-plans/{plan_id}/phases/{phase_id}/items",
        headers=headers,
        json={
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "procedure_code": "resina_oclusal",
            "finding_code": "restauracion",
        },
    )
    assert item_resp.status_code == 201, item_resp.text
    return plan_id, phase_id, item_resp.json()["id"]


async def test_add_item_sets_price_from_catalog_and_reflects_planned_on_odontogram(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    plan_id, _phase_id, item_id = await _make_plan_with_item(
        client, headers, patient_id, encounter_id
    )

    item_resp = await client.get(f"/api/v1/treatment-plans/{plan_id}", headers=headers)
    item = item_resp.json()["phases"][0]["items"][0]
    assert item["id"] == item_id
    assert item["unit_price"] == "500.00"
    assert item["subtotal"] == "500.00"

    odontogram = await client.get(f"/api/v1/patients/{patient_id}/odontogram", headers=headers)
    findings = odontogram.json()
    assert len(findings) == 1
    assert findings[0]["kind"] == "PLANNED"
    assert findings[0]["finding_code"] == "restauracion"


async def test_plan_detail_computes_phase_and_grand_totals(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    plan_id, phase_id, _item_id = await _make_plan_with_item(
        client, headers, patient_id, encounter_id
    )
    await client.post(
        f"/api/v1/treatment-plans/{plan_id}/phases/{phase_id}/items",
        headers=headers,
        json={"encounter_id": encounter_id, "procedure_code": "resina_oclusal", "quantity": 2},
    )

    detail = await client.get(f"/api/v1/treatment-plans/{plan_id}", headers=headers)
    body = detail.json()
    assert body["phases"][0]["phase_total"] == "1500.00"
    assert body["total"] == "1500.00"


async def test_apply_discount_reduces_subtotal_and_rejects_excess(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    plan_id, _phase_id, item_id = await _make_plan_with_item(
        client, headers, patient_id, encounter_id
    )

    too_much = await client.post(
        f"/api/v1/treatment-plans/{plan_id}/items/{item_id}/discount",
        headers=headers,
        json={"amount": "600.00", "reason": "Descuento excesivo"},
    )
    assert too_much.status_code == 422

    ok = await client.post(
        f"/api/v1/treatment-plans/{plan_id}/items/{item_id}/discount",
        headers=headers,
        json={"amount": "100.00", "reason": "Paciente de referido"},
    )
    assert ok.status_code == 200
    assert ok.json()["subtotal"] == "400.00"


async def test_items_cannot_be_added_after_plan_leaves_borrador(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    plan_id, phase_id, _item_id = await _make_plan_with_item(
        client, headers, patient_id, encounter_id
    )
    await client.patch(
        f"/api/v1/treatment-plans/{plan_id}/status", headers=headers, json={"status": "PRESENTADO"}
    )

    response = await client.post(
        f"/api/v1/treatment-plans/{plan_id}/phases/{phase_id}/items",
        headers=headers,
        json={"encounter_id": encounter_id, "procedure_code": "resina_oclusal"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == "PLAN_NOT_EDITABLE"


async def test_rejecting_a_plan_requires_reason(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    plan_id, _phase_id, _item_id = await _make_plan_with_item(
        client, headers, patient_id, encounter_id
    )
    await client.patch(
        f"/api/v1/treatment-plans/{plan_id}/status", headers=headers, json={"status": "PRESENTADO"}
    )

    without_reason = await client.patch(
        f"/api/v1/treatment-plans/{plan_id}/status", headers=headers, json={"status": "RECHAZADO"}
    )
    assert without_reason.status_code == 422

    with_reason = await client.patch(
        f"/api/v1/treatment-plans/{plan_id}/status",
        headers=headers,
        json={"status": "RECHAZADO", "reason": "El paciente no acepto el costo"},
    )
    assert with_reason.status_code == 200
    assert with_reason.json()["status"] == "RECHAZADO"


async def test_invalid_status_transition_is_rejected(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    plan_id, _phase_id, _item_id = await _make_plan_with_item(
        client, headers, patient_id, encounter_id
    )

    response = await client.patch(
        f"/api/v1/treatment-plans/{plan_id}/status", headers=headers, json={"status": "ACEPTADO"}
    )
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_TRANSITION"


async def test_accept_plan_partial_vs_total(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    plan_id, phase_id, item1_id = await _make_plan_with_item(
        client, headers, patient_id, encounter_id
    )
    item2_resp = await client.post(
        f"/api/v1/treatment-plans/{plan_id}/phases/{phase_id}/items",
        headers=headers,
        json={"encounter_id": encounter_id, "procedure_code": "resina_oclusal"},
    )
    item2_id = item2_resp.json()["id"]
    await client.patch(
        f"/api/v1/treatment-plans/{plan_id}/status", headers=headers, json={"status": "PRESENTADO"}
    )

    partial = await client.post(
        f"/api/v1/treatment-plans/{plan_id}/accept",
        headers=headers,
        json={"accepted_item_ids": [item1_id], "accepted_by_name": "Jose Perez"},
    )
    assert partial.status_code == 200
    assert partial.json()["status"] == "ACEPTADO"
    assert partial.json()["acceptance_type"] == "PARCIAL"

    detail = await client.get(f"/api/v1/treatment-plans/{plan_id}", headers=headers)
    items = detail.json()["phases"][0]["items"]
    accepted_map = {i["id"]: i["accepted"] for i in items}
    assert accepted_map[item1_id] is True
    assert accepted_map[item2_id] is False


async def test_register_performed_creates_odontogram_events_and_suggested_charge(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """Prueba obligatoria (reglas 3 y 4 de CLAUDE.md): lo planificado y lo realizado
    son entidades separadas (el planificado nunca se edita), y registrar lo realizado
    genera un cargo sugerido, nunca un pago."""
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    plan_id, _phase_id, item_id = await _make_plan_with_item(
        client, headers, patient_id, encounter_id
    )
    await client.patch(
        f"/api/v1/treatment-plans/{plan_id}/status", headers=headers, json={"status": "PRESENTADO"}
    )
    await client.post(
        f"/api/v1/treatment-plans/{plan_id}/accept",
        headers=headers,
        json={"accepted_item_ids": [item_id], "accepted_by_name": "Jose Perez"},
    )

    performed = await client.post(
        "/api/v1/procedures-performed",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "planned_id": item_id,
            "material": "resina compuesta A2",
        },
    )
    assert performed.status_code == 201, performed.text
    performed_body = performed.json()
    assert performed_body["procedure_code"] == "resina_oclusal"
    assert performed_body["tooth_fdi"] == 36
    assert performed_body["charge_amount"] == "500.00"

    # El planificado original sigue intacto (regla 3: entidades separadas).
    detail = await client.get(f"/api/v1/treatment-plans/{plan_id}", headers=headers)
    original_item = detail.json()["phases"][0]["items"][0]
    assert original_item["id"] == item_id
    assert original_item["is_active"] is True
    assert original_item["subtotal"] == "500.00"

    # El odontograma ahora tiene EXISTING y PERFORMED vigentes; el PLANNED se retiro.
    odontogram = await client.get(f"/api/v1/patients/{patient_id}/odontogram", headers=headers)
    kinds = {f["kind"] for f in odontogram.json()}
    assert kinds == {"EXISTING", "PERFORMED"}

    history = await client.get(f"/api/v1/patients/{patient_id}/teeth/36/history", headers=headers)
    planned_entries = [h for h in history.json() if h["kind"] == "PLANNED"]
    assert planned_entries[0]["is_current"] is False

    # Se genero un cargo (regla 4: no es un pago, solo una sugerencia de cobro -- su
    # estado se calcula contra los pagos aplicados, Fase 10). billing.read no lo tiene
    # el odontologo (separacion clinico/financiero ya establecida en el catalogo de
    # permisos), asi que se consulta con un admin_clinica.
    await make_user(email="admin@example.com", role_code="admin_clinica")
    admin_token = await _login(client, "admin@example.com")
    charges = await client.get(
        f"/api/v1/patients/{patient_id}/charges", headers=_headers(admin_token, clinic.id)
    )
    assert len(charges.json()) == 1
    assert charges.json()[0]["computed_status"] == "PENDIENTE"
    assert charges.json()[0]["amount"] == "500.00"


async def test_list_performed_returns_charge_amount_when_a_charge_exists(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """Bug de raiz encontrado en la Fase 12 probando el flujo completo en el
    navegador: list_performed() seguia desempacando billing_service.list_charges()
    como si devolviera Charge planos, cuando la Fase 10 lo cambio a tuplas
    (Charge, aplicado, saldo) -- GET /patients/{id}/procedures-performed tronaba
    con 500 en cuanto el paciente tenia al menos un cargo. Nunca habia una prueba
    de integracion para este endpoint de listado."""
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    plan_id, _phase_id, item_id = await _make_plan_with_item(
        client, headers, patient_id, encounter_id
    )
    await client.patch(
        f"/api/v1/treatment-plans/{plan_id}/status", headers=headers, json={"status": "PRESENTADO"}
    )
    await client.post(
        f"/api/v1/treatment-plans/{plan_id}/accept",
        headers=headers,
        json={"accepted_item_ids": [item_id], "accepted_by_name": "Jose Perez"},
    )
    await client.post(
        "/api/v1/procedures-performed",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "planned_id": item_id,
            "material": "resina compuesta A2",
        },
    )

    performed_list = await client.get(
        f"/api/v1/patients/{patient_id}/procedures-performed", headers=headers
    )
    assert performed_list.status_code == 200, performed_list.text
    body = performed_list.json()
    assert len(body) == 1
    assert body[0]["charge_amount"] == "500.00"


async def test_register_performed_ad_hoc_without_plan_uses_catalog_price(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    performed = await client.post(
        "/api/v1/procedures-performed",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "procedure_code": "resina_oclusal",
            "tooth_fdi": 46,
            "surface": "O",
            "finding_code": "restauracion",
        },
    )
    assert performed.status_code == 201, performed.text
    assert performed.json()["planned_id"] is None
    assert performed.json()["charge_amount"] == "500.00"


async def test_performed_procedures_pdf_endpoint_returns_a_pdf_document(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """Fase D (docs/clinica/ficha_reg_tratam_realizados.pdf): ficha 100%
    derivada de ProcedurePerformed, sin tabla nueva."""
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    performed = await client.post(
        "/api/v1/procedures-performed",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "procedure_code": "resina_oclusal",
            "tooth_fdi": 46,
            "surface": "O",
            "finding_code": "restauracion",
        },
    )
    assert performed.status_code == 201, performed.text

    response = await client.get(
        f"/api/v1/patients/{patient_id}/procedures-performed/pdf", headers=headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


async def test_performed_procedures_pdf_endpoint_requires_treatment_read(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, _encounter_id = await _setup(client, make_user, clinic, db_session)
    await make_user(email="asistente@example.com", role_code="asistente")
    asistente_token = await _login(client, "asistente@example.com")

    response = await client.get(
        f"/api/v1/patients/{patient_id}/procedures-performed/pdf",
        headers=_headers(asistente_token, clinic.id),
    )
    assert response.status_code == 403


async def test_plan_pdf_endpoint_returns_a_pdf_document(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    plan_id, _phase_id, _item_id = await _make_plan_with_item(
        client, headers, patient_id, encounter_id
    )

    response = await client.get(f"/api/v1/treatment-plans/{plan_id}/pdf", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


async def test_treatment_write_and_accept_budget_permissions_are_enforced(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    plan_id, _phase_id, item_id = await _make_plan_with_item(
        client, headers, patient_id, encounter_id
    )
    await client.patch(
        f"/api/v1/treatment-plans/{plan_id}/status", headers=headers, json={"status": "PRESENTADO"}
    )

    await make_user(email="recepcion@example.com", role_code="recepcion")
    recepcion_token = await _login(client, "recepcion@example.com")
    recepcion_headers = _headers(recepcion_token, clinic.id)

    denied_write = await client.post(
        f"/api/v1/treatment-plans/{plan_id}/phases",
        headers=recepcion_headers,
        json={"name": "Otra fase"},
    )
    assert denied_write.status_code == 403

    denied_accept = await client.post(
        f"/api/v1/treatment-plans/{plan_id}/accept",
        headers=recepcion_headers,
        json={"accepted_item_ids": [item_id], "accepted_by_name": "Jose Perez"},
    )
    assert denied_accept.status_code == 403
