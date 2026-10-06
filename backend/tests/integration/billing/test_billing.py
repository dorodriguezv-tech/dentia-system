from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patients.schemas import PatientCreateRequest
from app.modules.patients.service import create_patient


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _headers(token: str, clinic_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic_id)}


async def _setup_with_charge(client: AsyncClient, make_user, clinic, db_session: AsyncSession):
    """Crea paciente + atencion + un procedimiento realizado (genera un Charge de
    $500.00), y devuelve headers de admin_clinica (billing.read/write/configure) listos
    para usarse en las pruebas de cobranza."""
    await make_user(email="odonto@example.com", role_code="odontologo")
    odonto_token = await _login(client, "odonto@example.com")
    odonto_headers = _headers(odonto_token, clinic.id)

    patient = await create_patient(
        db_session,
        clinic_id=clinic.id,
        data=PatientCreateRequest(
            first_name="Jose", last_name_paternal="Perez", date_of_birth="1990-05-20"
        ),
        actor_id=None,
    )
    patient_id = str(patient.id)

    encounter_resp = await client.post(
        "/api/v1/encounters", headers=odonto_headers, json={"patient_id": patient_id}
    )
    assert encounter_resp.status_code == 201, encounter_resp.text
    encounter_id = encounter_resp.json()["id"]

    catalog_resp = await client.post(
        "/api/v1/procedure-catalog",
        headers=odonto_headers,
        json={"code": "resina_oclusal", "name": "Resina oclusal", "default_price": "500.00"},
    )
    assert catalog_resp.status_code == 201, catalog_resp.text

    performed_resp = await client.post(
        "/api/v1/procedures-performed",
        headers=odonto_headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "procedure_code": "resina_oclusal",
            "tooth_fdi": 36,
            "surface": "O",
        },
    )
    assert performed_resp.status_code == 201, performed_resp.text

    await make_user(email="admin@example.com", role_code="admin_clinica")
    admin_token = await _login(client, "admin@example.com")
    admin_headers = _headers(admin_token, clinic.id)

    charges_resp = await client.get(f"/api/v1/patients/{patient_id}/charges", headers=admin_headers)
    charge_id = charges_resp.json()[0]["id"]

    return admin_headers, patient_id, charge_id


async def test_charge_starts_pendiente_with_full_balance(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, _charge_id = await _setup_with_charge(
        client, make_user, clinic, db_session
    )
    charges = await client.get(f"/api/v1/patients/{patient_id}/charges", headers=headers)
    charge = charges.json()[0]
    assert charge["computed_status"] == "PENDIENTE"
    assert charge["balance"] == "500.00"
    assert charge["applied_amount"] == "0.00"


async def test_full_payment_marks_charge_as_pagado(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, charge_id = await _setup_with_charge(client, make_user, clinic, db_session)

    payment_resp = await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        headers=headers,
        json={
            "method": "efectivo",
            "amount": "500.00",
            "allocations": [{"charge_id": charge_id, "amount": "500.00"}],
        },
    )
    assert payment_resp.status_code == 201, payment_resp.text
    assert payment_resp.json()["allocated_amount"] == "500.00"
    assert payment_resp.json()["unallocated_amount"] == "0.00"

    charges = await client.get(f"/api/v1/patients/{patient_id}/charges", headers=headers)
    assert charges.json()[0]["computed_status"] == "PAGADO"
    assert charges.json()[0]["balance"] == "0.00"


async def test_partial_payment_marks_charge_as_parcial(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, charge_id = await _setup_with_charge(client, make_user, clinic, db_session)

    await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        headers=headers,
        json={
            "method": "tarjeta",
            "amount": "200.00",
            "reference": "AUTH123",
            "allocations": [{"charge_id": charge_id, "amount": "200.00"}],
        },
    )

    charges = await client.get(f"/api/v1/patients/{patient_id}/charges", headers=headers)
    assert charges.json()[0]["computed_status"] == "PARCIAL"
    assert charges.json()[0]["balance"] == "300.00"


async def test_payment_cannot_allocate_more_than_charge_balance(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, charge_id = await _setup_with_charge(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        headers=headers,
        json={
            "method": "efectivo",
            "amount": "1000.00",
            "allocations": [{"charge_id": charge_id, "amount": "600.00"}],
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "ALLOCATION_EXCEEDS_BALANCE"


async def test_payment_without_allocation_is_an_anticipo(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, _charge_id = await _setup_with_charge(
        client, make_user, clinic, db_session
    )

    payment_resp = await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        headers=headers,
        json={"method": "transferencia", "amount": "300.00", "reference": "SPEI-001"},
    )
    assert payment_resp.status_code == 201, payment_resp.text
    assert payment_resp.json()["allocated_amount"] == "0.00"
    assert payment_resp.json()["unallocated_amount"] == "300.00"

    summary = await client.get(f"/api/v1/patients/{patient_id}/billing-summary", headers=headers)
    assert summary.json()["total_credit"] == "300.00"


async def test_billing_summary_reflects_charges_and_payments(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, charge_id = await _setup_with_charge(client, make_user, clinic, db_session)
    await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        headers=headers,
        json={
            "method": "efectivo",
            "amount": "200.00",
            "allocations": [{"charge_id": charge_id, "amount": "200.00"}],
        },
    )

    summary = await client.get(f"/api/v1/patients/{patient_id}/billing-summary", headers=headers)
    body = summary.json()
    assert body["total_charged"] == "500.00"
    assert body["total_paid"] == "200.00"
    assert body["balance_due"] == "300.00"
    assert body["total_credit"] == "0.00"


async def test_cancel_payment_requires_reason_and_restores_balance(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, charge_id = await _setup_with_charge(client, make_user, clinic, db_session)
    payment_resp = await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        headers=headers,
        json={
            "method": "efectivo",
            "amount": "500.00",
            "allocations": [{"charge_id": charge_id, "amount": "500.00"}],
        },
    )
    payment_id = payment_resp.json()["id"]

    without_reason = await client.post(
        f"/api/v1/payments/{payment_id}/cancel", headers=headers, json={}
    )
    assert without_reason.status_code == 422

    with_reason = await client.post(
        f"/api/v1/payments/{payment_id}/cancel",
        headers=headers,
        json={"reason": "Pago duplicado por error"},
    )
    assert with_reason.status_code == 200
    assert with_reason.json()["is_active"] is False

    charges = await client.get(f"/api/v1/patients/{patient_id}/charges", headers=headers)
    assert charges.json()[0]["computed_status"] == "PENDIENTE"
    assert charges.json()[0]["balance"] == "500.00"


async def test_cancel_charge_with_payments_applied_is_blocked(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, charge_id = await _setup_with_charge(client, make_user, clinic, db_session)
    await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        headers=headers,
        json={
            "method": "efectivo",
            "amount": "100.00",
            "allocations": [{"charge_id": charge_id, "amount": "100.00"}],
        },
    )

    response = await client.post(
        f"/api/v1/charges/{charge_id}/cancel", headers=headers, json={"reason": "Prueba"}
    )
    assert response.status_code == 409
    assert response.json()["code"] == "CHARGE_HAS_PAYMENTS"


async def test_cancel_charge_without_payments_succeeds(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, charge_id = await _setup_with_charge(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/charges/{charge_id}/cancel",
        headers=headers,
        json={"reason": "Procedimiento registrado por error"},
    )
    assert response.status_code == 200
    assert response.json()["computed_status"] == "CANCELADO"


async def test_receipt_pdf_is_generated(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, charge_id = await _setup_with_charge(client, make_user, clinic, db_session)
    payment_resp = await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        headers=headers,
        json={
            "method": "efectivo",
            "amount": "500.00",
            "allocations": [{"charge_id": charge_id, "amount": "500.00"}],
        },
    )
    payment_id = payment_resp.json()["id"]

    receipt = await client.get(f"/api/v1/payments/{payment_id}/receipt", headers=headers)
    assert receipt.status_code == 200
    assert receipt.headers["content-type"] == "application/pdf"
    assert receipt.content.startswith(b"%PDF")


async def test_cash_session_open_close_and_totals(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, charge_id = await _setup_with_charge(client, make_user, clinic, db_session)

    open_resp = await client.post(
        "/api/v1/cash-sessions/open", headers=headers, json={"opening_amount": "1000.00"}
    )
    assert open_resp.status_code == 201, open_resp.text
    assert open_resp.json()["status"] == "ABIERTA"

    second_open = await client.post(
        "/api/v1/cash-sessions/open", headers=headers, json={"opening_amount": "500.00"}
    )
    assert second_open.status_code == 409
    assert second_open.json()["code"] == "CASH_SESSION_OPEN"

    await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        headers=headers,
        json={
            "method": "efectivo",
            "amount": "500.00",
            "allocations": [{"charge_id": charge_id, "amount": "500.00"}],
        },
    )

    current = await client.get("/api/v1/cash-sessions/current", headers=headers)
    assert current.json()["totals_by_method"]["efectivo"] == "500.00"
    assert current.json()["expected_cash"] == "1500.00"

    session_id = current.json()["id"]
    close_resp = await client.post(
        f"/api/v1/cash-sessions/{session_id}/close",
        headers=headers,
        json={"closing_amount": "1500.00"},
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "CERRADA"
    assert close_resp.json()["cash_difference"] == "0.00"

    still_current = await client.get("/api/v1/cash-sessions/current", headers=headers)
    assert still_current.json() is None


async def test_cash_session_difference_when_count_does_not_match(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, _charge_id = await _setup_with_charge(
        client, make_user, clinic, db_session
    )
    open_resp = await client.post(
        "/api/v1/cash-sessions/open", headers=headers, json={"opening_amount": "1000.00"}
    )
    session_id = open_resp.json()["id"]

    close_resp = await client.post(
        f"/api/v1/cash-sessions/{session_id}/close",
        headers=headers,
        json={"closing_amount": "950.00", "notes": "Faltante sin explicar"},
    )
    assert close_resp.json()["cash_difference"] == "-50.00"


async def test_billing_disabled_blocks_new_payments(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, charge_id = await _setup_with_charge(client, make_user, clinic, db_session)

    settings_resp = await client.put(
        "/api/v1/billing/settings", headers=headers, json={"billing_enabled": False}
    )
    assert settings_resp.status_code == 200
    assert settings_resp.json()["billing_enabled"] is False

    payment_resp = await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        headers=headers,
        json={
            "method": "efectivo",
            "amount": "100.00",
            "allocations": [{"charge_id": charge_id, "amount": "100.00"}],
        },
    )
    assert payment_resp.status_code == 403
    assert payment_resp.json()["code"] == "BILLING_DISABLED"

    # Reactivarla restaura el flujo normal.
    await client.put("/api/v1/billing/settings", headers=headers, json={"billing_enabled": True})
    retry = await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        headers=headers,
        json={
            "method": "efectivo",
            "amount": "100.00",
            "allocations": [{"charge_id": charge_id, "amount": "100.00"}],
        },
    )
    assert retry.status_code == 201


async def test_billing_disabled_does_not_block_charge_creation(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """Regla 4 + docs/PENDIENTES_CLINICOS: desactivar la cobranza (p.ej. clinicas
    universitarias) no impide que un procedimiento realizado siga generando su cargo
    sugerido -- es un registro clinico de lo que costaria, no un cobro de verdad."""
    headers, patient_id, _charge_id = await _setup_with_charge(
        client, make_user, clinic, db_session
    )
    await client.put("/api/v1/billing/settings", headers=headers, json={"billing_enabled": False})

    odonto_token = await _login(client, "odonto@example.com")
    odonto_headers = _headers(odonto_token, clinic.id)
    performed_resp = await odonto_headers_post_performed(client, odonto_headers, patient_id)
    assert performed_resp.status_code == 201, performed_resp.text


async def odonto_headers_post_performed(client: AsyncClient, headers: dict, patient_id: str):
    encounter_resp = await client.post(
        "/api/v1/encounters", headers=headers, json={"patient_id": patient_id}
    )
    encounter_id = encounter_resp.json()["id"]
    return await client.post(
        "/api/v1/procedures-performed",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "procedure_code": "resina_oclusal",
            "tooth_fdi": 46,
            "surface": "O",
        },
    )


async def test_billing_settings_read_allowed_for_billing_read_but_not_write_denied(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """GET /billing/settings solo exige billing.read (caja lo tiene, para poder decidir
    si mostrar la pestana Cuenta); PUT exige billing.configure, que caja no tiene."""
    headers, _patient_id, _charge_id = await _setup_with_charge(
        client, make_user, clinic, db_session
    )
    await make_user(email="caja@example.com", role_code="caja")
    caja_token = await _login(client, "caja@example.com")
    caja_headers = _headers(caja_token, clinic.id)

    get_resp = await client.get("/api/v1/billing/settings", headers=caja_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["billing_enabled"] is True

    put_resp = await client.put(
        "/api/v1/billing/settings", headers=caja_headers, json={"billing_enabled": False}
    )
    assert put_resp.status_code == 403


async def test_billing_write_denied_for_role_without_permission(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, charge_id = await _setup_with_charge(client, make_user, clinic, db_session)
    odonto_token = await _login(client, "odonto@example.com")

    response = await client.post(
        f"/api/v1/patients/{patient_id}/payments",
        headers=_headers(odonto_token, clinic.id),
        json={
            "method": "efectivo",
            "amount": "100.00",
            "allocations": [{"charge_id": charge_id, "amount": "100.00"}],
        },
    )
    assert response.status_code == 403
