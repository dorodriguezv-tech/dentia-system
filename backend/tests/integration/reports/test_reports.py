import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import AiSuggestion
from app.modules.patients.schemas import PatientCreateRequest
from app.modules.patients.service import create_patient
from app.modules.treatment.models import TreatmentPlan


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _headers(token: str, clinic_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic_id)}


async def _setup(client: AsyncClient, make_user, clinic, db_session: AsyncSession):
    """Siembra un escenario completo para los reportes: un paciente con un
    procedimiento realizado (y su cargo de $500.00), una cita TERMINADA y otra
    NO_SHOW, un plan de tratamiento BORRADOR y otro ACEPTADO, y dos sugerencias de
    IA (una aceptada, otra pendiente). Devuelve headers de admin_clinica, caja y
    odontologo (sin `reports.read`) listos para usarse en las pruebas."""
    odonto_user = await make_user(email="odonto@example.com", role_code="odontologo")
    odonto_headers = _headers(await _login(client, "odonto@example.com"), clinic.id)

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

    provider_resp = await client.post(
        "/api/v1/providers", headers=odonto_headers, json={"user_id": str(odonto_user.id)}
    )
    assert provider_resp.status_code == 201, provider_resp.text
    provider_id = provider_resp.json()["id"]

    now = datetime.now(UTC)
    terminada_resp = await client.post(
        "/api/v1/appointments",
        headers=odonto_headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": (now + timedelta(hours=1)).isoformat(),
        },
    )
    assert terminada_resp.status_code == 201, terminada_resp.text
    terminada_id = terminada_resp.json()["id"]
    await client.patch(
        f"/api/v1/appointments/{terminada_id}/status",
        headers=odonto_headers,
        json={"status": "CONFIRMADA"},
    )
    await client.patch(
        f"/api/v1/appointments/{terminada_id}/status",
        headers=odonto_headers,
        json={"status": "EN_ATENCION"},
    )
    await client.patch(
        f"/api/v1/appointments/{terminada_id}/status",
        headers=odonto_headers,
        json={"status": "TERMINADA"},
    )

    no_show_resp = await client.post(
        "/api/v1/appointments",
        headers=odonto_headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": (now + timedelta(hours=3)).isoformat(),
        },
    )
    assert no_show_resp.status_code == 201, no_show_resp.text
    no_show_id = no_show_resp.json()["id"]
    await client.patch(
        f"/api/v1/appointments/{no_show_id}/status",
        headers=odonto_headers,
        json={"status": "NO_SHOW", "reason": "No se presento"},
    )

    db_session.add_all(
        [
            TreatmentPlan(
                clinic_id=clinic.id,
                patient_id=patient.id,
                encounter_id=uuid.UUID(encounter_id),
                professional_id=odonto_user.id,
                title="Plan en borrador",
                status="BORRADOR",
            ),
            TreatmentPlan(
                clinic_id=clinic.id,
                patient_id=patient.id,
                encounter_id=uuid.UUID(encounter_id),
                professional_id=odonto_user.id,
                title="Plan aceptado",
                status="ACEPTADO",
                accepted_at=now,
                accepted_by_name="Jose Perez",
            ),
            AiSuggestion(
                clinic_id=clinic.id,
                patient_id=patient.id,
                encounter_id=uuid.UUID(encounter_id),
                batch_id=uuid.uuid4(),
                action_type="add_vital_signs",
                payload={"heart_rate": 70},
                status="ACCEPTED",
                model_name="qwen2.5:7b",
                reviewed_at=now,
                reviewed_by=odonto_user.id,
            ),
            AiSuggestion(
                clinic_id=clinic.id,
                patient_id=patient.id,
                encounter_id=uuid.UUID(encounter_id),
                batch_id=uuid.uuid4(),
                action_type="set_chief_complaint",
                payload={"text": "dolor"},
                status="PENDING",
                model_name="qwen2.5:7b",
            ),
        ]
    )
    await db_session.commit()

    await make_user(email="admin@example.com", role_code="admin_clinica")
    admin_headers = _headers(await _login(client, "admin@example.com"), clinic.id)

    await make_user(email="caja@example.com", role_code="caja")
    caja_headers = _headers(await _login(client, "caja@example.com"), clinic.id)

    return {
        "admin": admin_headers,
        "caja": caja_headers,
        "odonto": odonto_headers,
        "patient_id": patient_id,
    }


def _date_range_params(days: int = 2) -> dict[str, str]:
    now = datetime.now(UTC)
    return {
        "date_from": (now - timedelta(days=days)).date().isoformat(),
        "date_to": (now + timedelta(days=days)).date().isoformat(),
    }


# --------------------------------------------------------------------- permisos


async def test_odontologo_without_reports_read_gets_403(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, make_user, clinic, db_session)
    resp = await client.get(
        "/api/v1/reports/patients", headers=ctx["odonto"], params=_date_range_params()
    )
    assert resp.status_code == 403


async def test_caja_can_read_reports(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, make_user, clinic, db_session)
    resp = await client.get(
        "/api/v1/reports/patients", headers=ctx["caja"], params=_date_range_params()
    )
    assert resp.status_code == 200


async def test_invalid_date_range_returns_400(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, make_user, clinic, db_session)
    resp = await client.get(
        "/api/v1/reports/patients",
        headers=ctx["admin"],
        params={"date_from": "2026-02-01", "date_to": "2026-01-01"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_DATE_RANGE"


# --------------------------------------------------------------------- 1. pacientes


async def test_patients_report_counts_new_and_active(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, make_user, clinic, db_session)
    resp = await client.get(
        "/api/v1/reports/patients", headers=ctx["admin"], params=_date_range_params()
    )
    body = resp.json()
    assert body["new_patients"] == 1
    assert body["active_patients"] == 1
    assert len(body["rows"]) == 1


async def test_patients_report_export_is_csv_and_audited(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, make_user, clinic, db_session)
    resp = await client.get(
        "/api/v1/reports/patients/export", headers=ctx["admin"], params=_date_range_params()
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "Jose Perez" in resp.text

    from sqlalchemy import select

    from app.audit.models import AuditEvent

    events = (
        (await db_session.execute(select(AuditEvent).where(AuditEvent.action == "reports.export")))
        .scalars()
        .all()
    )
    assert len(events) == 1
    assert events[0].entity_id == "patients"


# ---------------------------------------------------------------------- 2. agenda


async def test_appointments_report_counts_by_status_and_no_show_rate(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, make_user, clinic, db_session)
    resp = await client.get(
        "/api/v1/reports/appointments", headers=ctx["admin"], params=_date_range_params()
    )
    body = resp.json()
    assert body["counts_by_status"]["TERMINADA"] == 1
    assert body["counts_by_status"]["NO_SHOW"] == 1
    assert body["no_show_rate"] == "50.00"
    assert len(body["rows"]) == 2


# ------------------------------------------------------------------- 3. produccion


async def test_production_report_sums_by_professional(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, make_user, clinic, db_session)
    resp = await client.get(
        "/api/v1/reports/production", headers=ctx["admin"], params=_date_range_params()
    )
    body = resp.json()
    assert body["total_amount"] == "500.00"
    assert len(body["by_professional"]) == 1
    assert body["by_professional"][0]["total_amount"] == "500.00"
    assert body["by_professional"][0]["professional_name"] == "Usuario de prueba"


# ------------------------------------------------------------------------ 4. planes


async def test_treatment_plans_report_pending_vs_accepted(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, make_user, clinic, db_session)
    resp = await client.get(
        "/api/v1/reports/treatment-plans", headers=ctx["admin"], params=_date_range_params()
    )
    body = resp.json()
    assert body["pending_count"] == 1
    assert body["accepted_count"] == 1
    assert body["counts_by_status"] == {"BORRADOR": 1, "ACEPTADO": 1}


# ---------------------------------------------------------- 5. cuentas por cobrar


async def test_accounts_receivable_report_lists_pending_balance(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, make_user, clinic, db_session)
    resp = await client.get("/api/v1/reports/accounts-receivable", headers=ctx["admin"])
    body = resp.json()
    assert body["total_balance_due"] == "500.00"
    assert len(body["rows"]) == 1
    assert body["rows"][0]["computed_status"] == "PENDIENTE"


async def test_accounts_receivable_excludes_fully_paid_charge(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, make_user, clinic, db_session)
    charges_resp = await client.get(
        f"/api/v1/patients/{ctx['patient_id']}/charges", headers=ctx["admin"]
    )
    charge_id = charges_resp.json()[0]["id"]
    await client.post(
        f"/api/v1/patients/{ctx['patient_id']}/payments",
        headers=ctx["admin"],
        json={
            "method": "efectivo",
            "amount": "500.00",
            "allocations": [{"charge_id": charge_id, "amount": "500.00"}],
        },
    )
    resp = await client.get("/api/v1/reports/accounts-receivable", headers=ctx["admin"])
    body = resp.json()
    assert body["total_balance_due"] == "0.00"
    assert body["rows"] == []


# ------------------------------------------------------------------------- 6. IA


async def test_ai_usage_report_counts_by_status_and_action(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, make_user, clinic, db_session)
    resp = await client.get(
        "/api/v1/reports/ai-usage", headers=ctx["admin"], params=_date_range_params()
    )
    body = resp.json()
    assert body["counts_by_status"] == {"ACCEPTED": 1, "PENDING": 1}
    assert body["counts_by_action_type"] == {"add_vital_signs": 1, "set_chief_complaint": 1}


# --------------------------------------------------------------- tablero por rol


async def test_dashboard_shows_sections_matching_caja_permissions(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, make_user, clinic, db_session)
    resp = await client.get("/api/v1/reports/dashboard", headers=ctx["caja"])
    body = resp.json()
    # caja tiene patients.read y billing.read, pero no agenda.read ni treatment.read
    # (docs/MATRIZ_PERMISOS.md) -- el tablero solo debe traer esas dos secciones.
    assert body["patients"] is not None
    assert body["billing"] is not None
    assert body["agenda_today"] is None
    assert body["treatment"] is None
    assert body["ai_usage"] is None
    assert body["billing"]["balance_due_total"] == "500.00"


async def test_dashboard_shows_agenda_and_treatment_for_odontologo(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    ctx = await _setup(client, make_user, clinic, db_session)
    resp = await client.get("/api/v1/reports/dashboard", headers=ctx["odonto"])
    body = resp.json()
    # odontologo no tiene billing.read (docs/MATRIZ_PERMISOS.md), pero si
    # patients.read, agenda.read, treatment.read y ai.use.
    assert body["billing"] is None
    assert body["patients"] is not None
    assert body["agenda_today"] is not None
    assert body["treatment"] is not None
    assert body["treatment"]["pending_plans"] == 1
    assert body["ai_usage"] is not None
    assert body["ai_usage"]["pending_review"] == 1


async def test_dashboard_does_not_require_reports_read(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """A diferencia de la pantalla "Reportes" completa, el tablero de inicio es solo
    autenticacion + sucursal -- cada seccion se filtra por su propio permiso."""
    ctx = await _setup(client, make_user, clinic, db_session)
    resp = await client.get("/api/v1/reports/dashboard", headers=ctx["odonto"])
    assert resp.status_code == 200
