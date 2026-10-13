from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.encounters.models import Encounter
from app.modules.patients.schemas import PatientCreateRequest
from app.modules.patients.service import create_patient


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _headers(token: str, clinic_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic_id)}


async def _odontologo_token(client: AsyncClient, make_user, clinic) -> str:
    await make_user(email="odonto@example.com", role_code="odontologo")
    return await _login(client, "odonto@example.com")


async def _make_patient(db_session: AsyncSession, clinic, actor_id) -> str:
    patient = await create_patient(
        db_session,
        clinic_id=clinic.id,
        data=PatientCreateRequest(
            first_name="Jose", last_name_paternal="Perez", date_of_birth="1990-05-20"
        ),
        actor_id=actor_id,
    )
    return str(patient.id)


async def _create_encounter(
    client: AsyncClient, headers: dict, db_session: AsyncSession, clinic, actor_id
) -> str:
    patient_id = await _make_patient(db_session, clinic, actor_id)
    response = await client.post(
        "/api/v1/encounters", headers=headers, json={"patient_id": patient_id}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_create_encounter_denied_without_records_write(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    await make_user(email="recepcion@example.com", role_code="recepcion")
    token = await _login(client, "recepcion@example.com")
    admin_user_id = (await make_user(email="odonto2@example.com", role_code="odontologo")).id
    patient_id = await _make_patient(db_session, clinic, admin_user_id)

    response = await client.post(
        "/api/v1/encounters",
        headers=_headers(token, clinic.id),
        json={"patient_id": patient_id},
    )
    assert response.status_code == 403


async def test_create_note_and_autosave_draft(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    token = await _odontologo_token(client, make_user, clinic)
    headers = _headers(token, clinic.id)
    encounter_id = await _create_encounter(client, headers, db_session, clinic, None)

    created = await client.post(
        f"/api/v1/encounters/{encounter_id}/notes",
        headers=headers,
        json={"soap_s": "Dolor al frio"},
    )
    assert created.status_code == 201
    note = created.json()
    assert note["status"] == "DRAFT"
    assert note["version"] == 1

    updated = await client.patch(
        f"/api/v1/notes/{note['id']}", headers=headers, json={"soap_o": "Caries en 36"}
    )
    assert updated.status_code == 200
    assert updated.json()["soap_o"] == "Caries en 36"
    assert updated.json()["soap_s"] == "Dolor al frio"


async def test_finalize_note_without_alerts_succeeds(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    token = await _odontologo_token(client, make_user, clinic)
    headers = _headers(token, clinic.id)
    encounter_id = await _create_encounter(client, headers, db_session, clinic, None)
    note = (
        await client.post(
            f"/api/v1/encounters/{encounter_id}/notes", headers=headers, json={"soap_s": "Bien"}
        )
    ).json()

    response = await client.post(f"/api/v1/notes/{note['id']}/finalize", headers=headers, json={})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "FINAL"
    assert body["content_hash"] is not None


async def test_finalize_note_with_alerts_requires_acknowledgement(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    token = await _odontologo_token(client, make_user, clinic)
    headers = _headers(token, clinic.id)
    encounter_id = await _create_encounter(client, headers, db_session, clinic, None)
    encounter = (await client.get(f"/api/v1/encounters/{encounter_id}", headers=headers)).json()
    patient_id = encounter["patient_id"]

    await client.post(
        f"/api/v1/patients/{patient_id}/allergies",
        headers=headers,
        json={"encounter_id": encounter_id, "substance": "Penicilina", "severity": "severa"},
    )

    note = (
        await client.post(
            f"/api/v1/encounters/{encounter_id}/notes", headers=headers, json={"soap_s": "Bien"}
        )
    ).json()

    denied = await client.post(f"/api/v1/notes/{note['id']}/finalize", headers=headers, json={})
    assert denied.status_code == 400
    assert denied.json()["code"] == "ALERTS_NOT_ACKNOWLEDGED"
    assert "Alergia severa: Penicilina" in denied.json()["details"]["alerts"]

    accepted = await client.post(
        f"/api/v1/notes/{note['id']}/finalize",
        headers=headers,
        json={"alerts_acknowledged": True},
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "FINAL"


async def test_final_note_cannot_be_edited(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """Prueba obligatoria (CLAUDE.md regla 1): una nota FINAL no se puede editar."""
    token = await _odontologo_token(client, make_user, clinic)
    headers = _headers(token, clinic.id)
    encounter_id = await _create_encounter(client, headers, db_session, clinic, None)
    note = (
        await client.post(
            f"/api/v1/encounters/{encounter_id}/notes", headers=headers, json={"soap_s": "Bien"}
        )
    ).json()
    await client.post(f"/api/v1/notes/{note['id']}/finalize", headers=headers, json={})

    response = await client.patch(
        f"/api/v1/notes/{note['id']}", headers=headers, json={"soap_s": "Intento de cambio"}
    )
    assert response.status_code == 403
    assert response.json()["code"] == "NOTE_NOT_EDITABLE"


async def test_correct_final_note_creates_new_version(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    token = await _odontologo_token(client, make_user, clinic)
    headers = _headers(token, clinic.id)
    encounter_id = await _create_encounter(client, headers, db_session, clinic, None)
    note = (
        await client.post(
            f"/api/v1/encounters/{encounter_id}/notes",
            headers=headers,
            json={"soap_s": "Version original"},
        )
    ).json()
    await client.post(f"/api/v1/notes/{note['id']}/finalize", headers=headers, json={})

    corrected = await client.post(
        f"/api/v1/notes/{note['id']}/correct",
        headers=headers,
        json={"reason": "Se me olvido registrar la alergia"},
    )
    assert corrected.status_code == 200
    new_note = corrected.json()
    assert new_note["status"] == "DRAFT"
    assert new_note["version"] == 2
    assert new_note["previous_version_id"] == note["id"]
    assert new_note["soap_s"] == "Version original"

    old_note = (await client.get(f"/api/v1/notes/{note['id']}", headers=headers)).json()
    assert old_note["status"] == "CORRECTED"
    assert old_note["soap_s"] == "Version original"


async def test_correct_requires_the_note_to_be_final(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    token = await _odontologo_token(client, make_user, clinic)
    headers = _headers(token, clinic.id)
    encounter_id = await _create_encounter(client, headers, db_session, clinic, None)
    note = (
        await client.post(
            f"/api/v1/encounters/{encounter_id}/notes", headers=headers, json={"soap_s": "Borrador"}
        )
    ).json()

    response = await client.post(
        f"/api/v1/notes/{note['id']}/correct", headers=headers, json={"reason": "x"}
    )
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_TRANSITION"


async def test_cancel_draft_note_requires_reason(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    token = await _odontologo_token(client, make_user, clinic)
    headers = _headers(token, clinic.id)
    encounter_id = await _create_encounter(client, headers, db_session, clinic, None)
    note = (
        await client.post(
            f"/api/v1/encounters/{encounter_id}/notes", headers=headers, json={"soap_s": "x"}
        )
    ).json()

    missing_reason = await client.post(
        f"/api/v1/notes/{note['id']}/cancel", headers=headers, json={"reason": ""}
    )
    assert missing_reason.status_code == 422

    cancelled = await client.post(
        f"/api/v1/notes/{note['id']}/cancel",
        headers=headers,
        json={"reason": "Paciente no se presento"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    assert cancelled.json()["cancel_reason"] == "Paciente no se presento"


async def test_timeline_includes_encounter_and_notes(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    token = await _odontologo_token(client, make_user, clinic)
    headers = _headers(token, clinic.id)
    encounter_id = await _create_encounter(client, headers, db_session, clinic, None)
    encounter = (await client.get(f"/api/v1/encounters/{encounter_id}", headers=headers)).json()
    await client.post(
        f"/api/v1/encounters/{encounter_id}/notes", headers=headers, json={"soap_s": "x"}
    )

    timeline = await client.get(
        f"/api/v1/patients/{encounter['patient_id']}/timeline", headers=headers
    )
    assert timeline.status_code == 200
    entries = timeline.json()
    assert len(entries) == 1
    assert entries[0]["encounter_id"] == encounter_id
    assert len(entries[0]["notes"]) == 1


# ------------------------------------------------------------ B10: GET /encounters/current


async def test_current_encounter_is_null_without_an_open_encounter(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")

    response = await client.get("/api/v1/encounters/current", headers=_headers(token, clinic.id))

    assert response.status_code == 200
    assert response.json() is None


async def test_current_encounter_returns_the_open_one_started_today(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    odonto = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)
    encounter_id = await _create_encounter(client, headers, db_session, clinic, odonto.id)

    response = await client.get("/api/v1/encounters/current", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body is not None
    assert body["id"] == encounter_id
    assert body["patient_full_name"] == "Jose Perez"


async def test_current_encounter_ignores_another_professionals_open_encounter(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    odonto_a = await make_user(email="odonto-a@example.com", role_code="odontologo")
    token_a = await _login(client, "odonto-a@example.com")
    await _create_encounter(client, _headers(token_a, clinic.id), db_session, clinic, odonto_a.id)

    await make_user(email="odonto-b@example.com", role_code="odontologo")
    token_b = await _login(client, "odonto-b@example.com")

    response = await client.get("/api/v1/encounters/current", headers=_headers(token_b, clinic.id))

    assert response.status_code == 200
    assert response.json() is None


async def test_current_encounter_ignores_one_started_a_previous_day(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    # Limitacion documentada en docs/PENDIENTES_CLINICOS.md #51: hasta que exista
    # un cierre real (B11), "actual" se limita a hoy, para no mostrar como abierta
    # una atencion de hace semanas que nadie cerro formalmente.
    odonto = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)
    encounter_id = await _create_encounter(client, headers, db_session, clinic, odonto.id)

    encounter = await db_session.get(Encounter, encounter_id)
    assert encounter is not None
    encounter.started_at = datetime.now(UTC) - timedelta(days=2)
    await db_session.commit()

    response = await client.get("/api/v1/encounters/current", headers=headers)

    assert response.status_code == 200
    assert response.json() is None


async def test_current_encounter_requires_records_write(
    client: AsyncClient, make_user, clinic
) -> None:
    await make_user(email="recepcion@example.com", role_code="recepcion")
    token = await _login(client, "recepcion@example.com")

    response = await client.get("/api/v1/encounters/current", headers=_headers(token, clinic.id))

    assert response.status_code == 403
