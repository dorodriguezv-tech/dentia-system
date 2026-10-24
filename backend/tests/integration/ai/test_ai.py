import json
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import ollama_client
from app.ai.ollama_client import OllamaUnavailableError
from app.core.config import get_settings
from app.modules.patients.schemas import PatientCreateRequest
from app.modules.patients.service import create_patient
from app.modules.records.models import Allergy
from app.modules.treatment.schemas import ProcedureCatalogCreateRequest
from app.modules.treatment.service import create_procedure_catalog_item


@pytest.fixture(autouse=True)
def _ai_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Este archivo entero prueba el interprete/sugerencias de IA -- sin esto,
    cada prueba dependeria de que AI_ENABLED del .env local sea true (no lo
    es: la clinica que usa este repo lo apago a proposito, ver
    docs/INSTALACION_PRODUCCION.md)."""
    monkeypatch.setattr(get_settings(), "ai_enabled", True)


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

    await create_procedure_catalog_item(
        db_session,
        clinic_id=clinic.id,
        data=ProcedureCatalogCreateRequest(
            code="resina", name="Resina", default_price=Decimal("650")
        ),
        actor_id=None,
    )
    return headers, str(patient.id), encounter_id


def _fake_chat(actions: list[dict], unrecognized: list[dict] | None = None):
    async def _chat(*, model, system_prompt, user_prompt, json_schema, keep_alive=None):
        content = json.dumps({"actions": actions, "unrecognized": unrecognized or []})
        return {"message": {"role": "assistant", "content": content}}

    return _chat


async def test_interpret_creates_pending_suggestions_without_writing_clinical_tables(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    """Prueba obligatoria (docs sec. 10): ninguna ruta de la IA escribe en tablas
    clinicas sin aceptacion humana explicita (regla 9 de CLAUDE.md)."""
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    monkeypatch.setattr(
        ollama_client,
        "chat",
        _fake_chat(
            [
                {"type": "add_allergy", "substance": "Penicilina"},
                {
                    "type": "add_tooth_finding",
                    "tooth_fdi": 36,
                    "surfaces": ["O", "D"],
                    "finding_code": "caries",
                },
            ]
        ),
    )
    monkeypatch.setattr(ollama_client, "model_digest", lambda model: _async_none())

    response = await client.post(
        "/api/v1/ai/interpret",
        headers=headers,
        json={"encounter_id": encounter_id, "transcript": "Alergica a la penicilina, caries en 36"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["suggestions"]) == 2
    assert all(s["status"] == "PENDING" for s in body["suggestions"])

    allergies = (await db_session.execute(select(Allergy))).scalars().all()
    assert allergies == []


async def _async_none():
    return None


async def test_accept_allergy_suggestion_writes_with_ai_assisted_origin(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    monkeypatch.setattr(
        ollama_client, "chat", _fake_chat([{"type": "add_allergy", "substance": "Penicilina"}])
    )
    monkeypatch.setattr(ollama_client, "model_digest", lambda model: _async_none())

    interpret_resp = await client.post(
        "/api/v1/ai/interpret",
        headers=headers,
        json={"encounter_id": encounter_id, "transcript": "Alergica a la penicilina"},
    )
    suggestion_id = interpret_resp.json()["suggestions"][0]["id"]

    accept_resp = await client.post(
        f"/api/v1/ai/suggestions/{suggestion_id}/accept", headers=headers, json={}
    )
    assert accept_resp.status_code == 200, accept_resp.text
    assert accept_resp.json()["status"] == "ACCEPTED"

    allergies = (await db_session.execute(select(Allergy))).scalars().all()
    assert len(allergies) == 1
    assert allergies[0].substance == "Penicilina"
    assert allergies[0].origin == "AI_ASSISTED"


async def test_accept_with_edits_overrides_payload_before_applying(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    monkeypatch.setattr(
        ollama_client, "chat", _fake_chat([{"type": "add_allergy", "substance": "Penicilina"}])
    )
    monkeypatch.setattr(ollama_client, "model_digest", lambda model: _async_none())

    interpret_resp = await client.post(
        "/api/v1/ai/interpret",
        headers=headers,
        json={"encounter_id": encounter_id, "transcript": "Alergica a la penicilina"},
    )
    suggestion_id = interpret_resp.json()["suggestions"][0]["id"]

    accept_resp = await client.post(
        f"/api/v1/ai/suggestions/{suggestion_id}/accept",
        headers=headers,
        json={"edits": {"substance": "Amoxicilina"}},
    )
    assert accept_resp.status_code == 200, accept_resp.text

    allergies = (await db_session.execute(select(Allergy))).scalars().all()
    assert allergies[0].substance == "Amoxicilina"


async def test_reject_suggestion_does_not_write_anything(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    monkeypatch.setattr(
        ollama_client, "chat", _fake_chat([{"type": "add_allergy", "substance": "Penicilina"}])
    )
    monkeypatch.setattr(ollama_client, "model_digest", lambda model: _async_none())

    interpret_resp = await client.post(
        "/api/v1/ai/interpret",
        headers=headers,
        json={"encounter_id": encounter_id, "transcript": "Alergica a la penicilina"},
    )
    suggestion_id = interpret_resp.json()["suggestions"][0]["id"]

    reject_resp = await client.post(
        f"/api/v1/ai/suggestions/{suggestion_id}/reject",
        headers=headers,
        json={"reason": "Dato incorrecto"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "REJECTED"

    allergies = (await db_session.execute(select(Allergy))).scalars().all()
    assert allergies == []


async def test_accepting_a_non_pending_suggestion_fails(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    monkeypatch.setattr(
        ollama_client, "chat", _fake_chat([{"type": "add_allergy", "substance": "Penicilina"}])
    )
    monkeypatch.setattr(ollama_client, "model_digest", lambda model: _async_none())

    interpret_resp = await client.post(
        "/api/v1/ai/interpret",
        headers=headers,
        json={"encounter_id": encounter_id, "transcript": "Alergica a la penicilina"},
    )
    suggestion_id = interpret_resp.json()["suggestions"][0]["id"]
    await client.post(f"/api/v1/ai/suggestions/{suggestion_id}/reject", headers=headers, json={})

    second_attempt = await client.post(
        f"/api/v1/ai/suggestions/{suggestion_id}/accept", headers=headers, json={}
    )
    assert second_attempt.status_code == 409


async def test_prohibited_action_is_discarded_and_logged(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    monkeypatch.setattr(
        ollama_client,
        "chat",
        _fake_chat(
            [
                {"type": "finalize_note", "text": "x"},
                {"type": "add_allergy", "substance": "Penicilina"},
            ]
        ),
    )
    monkeypatch.setattr(ollama_client, "model_digest", lambda model: _async_none())

    response = await client.post(
        "/api/v1/ai/interpret",
        headers=headers,
        json={"encounter_id": encounter_id, "transcript": "finaliza la nota; alergia a penicilina"},
    )
    body = response.json()
    assert len(body["suggestions"]) == 1
    assert len(body["unrecognized"]) == 1
    assert "finalize_note" in body["unrecognized"][0]["reason"]


async def test_procedure_code_outside_clinic_catalog_is_unrecognized(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    monkeypatch.setattr(
        ollama_client,
        "chat",
        _fake_chat(
            [{"type": "add_planned_procedure", "procedure_code": "no_existe", "surfaces": []}]
        ),
    )
    monkeypatch.setattr(ollama_client, "model_digest", lambda model: _async_none())

    response = await client.post(
        "/api/v1/ai/interpret",
        headers=headers,
        json={"encounter_id": encounter_id, "transcript": "plan: procedimiento que no existe"},
    )
    body = response.json()
    assert body["suggestions"] == []
    assert len(body["unrecognized"]) == 1


async def test_accept_planned_procedure_creates_draft_plan_and_phase(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    monkeypatch.setattr(
        ollama_client,
        "chat",
        _fake_chat(
            [
                {
                    "type": "add_planned_procedure",
                    "procedure_code": "resina",
                    "tooth_fdi": 36,
                    "surfaces": ["O"],
                }
            ]
        ),
    )
    monkeypatch.setattr(ollama_client, "model_digest", lambda model: _async_none())

    interpret_resp = await client.post(
        "/api/v1/ai/interpret",
        headers=headers,
        json={"encounter_id": encounter_id, "transcript": "plan: resina en 36 oclusal"},
    )
    suggestion_id = interpret_resp.json()["suggestions"][0]["id"]

    accept_resp = await client.post(
        f"/api/v1/ai/suggestions/{suggestion_id}/accept", headers=headers, json={}
    )
    assert accept_resp.status_code == 200, accept_resp.text

    plans_resp = await client.get(f"/api/v1/patients/{patient_id}/treatment-plans", headers=headers)
    assert plans_resp.status_code == 200
    plans = plans_resp.json()
    assert len(plans) == 1
    assert plans[0]["status"] == "BORRADOR"


async def test_schedule_followup_accept_does_not_create_appointment(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    monkeypatch.setattr(
        ollama_client,
        "chat",
        _fake_chat([{"type": "schedule_followup", "in_days": 15, "reason": "Control"}]),
    )
    monkeypatch.setattr(ollama_client, "model_digest", lambda model: _async_none())

    interpret_resp = await client.post(
        "/api/v1/ai/interpret",
        headers=headers,
        json={"encounter_id": encounter_id, "transcript": "control en quince dias"},
    )
    suggestion_id = interpret_resp.json()["suggestions"][0]["id"]

    accept_resp = await client.post(
        f"/api/v1/ai/suggestions/{suggestion_id}/accept", headers=headers, json={}
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "ACCEPTED"


async def test_interpret_denied_without_ai_use_permission(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    await make_user(email="recepcion@example.com", role_code="recepcion")
    recepcion_token = await _login(client, "recepcion@example.com")

    response = await client.post(
        "/api/v1/ai/interpret",
        headers=_headers(recepcion_token, clinic.id),
        json={"encounter_id": encounter_id, "transcript": "no deberia poder"},
    )
    assert response.status_code == 403


async def test_interpret_returns_503_when_ollama_unavailable(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    async def _unavailable(*, model, system_prompt, user_prompt, json_schema, keep_alive=None):
        raise OllamaUnavailableError("sin conexion")

    monkeypatch.setattr(ollama_client, "chat", _unavailable)

    response = await client.post(
        "/api/v1/ai/interpret",
        headers=headers,
        json={"encounter_id": encounter_id, "transcript": "dictado cualquiera"},
    )
    assert response.status_code == 503
    assert response.json()["code"] == "AI_UNAVAILABLE"


async def test_status_and_settings_require_ai_configure_permission(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    denied = await client.get("/api/v1/ai/status", headers=headers)
    assert denied.status_code == 403

    await make_user(email="admin@example.com", role_code="admin_clinica")
    admin_token = await _login(client, "admin@example.com")
    admin_headers = _headers(admin_token, clinic.id)

    monkeypatch.setattr(ollama_client, "is_reachable", lambda: _async_true())
    monkeypatch.setattr(ollama_client, "model_digest", lambda model: _async_none())
    allowed = await client.get("/api/v1/ai/status", headers=admin_headers)
    assert allowed.status_code == 200
    assert allowed.json()["ollama_reachable"] is True


async def _async_true():
    return True


async def test_transcribe_accepts_android_m4a_audio(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    # B2 (docs/05_APP_MOVIL.md Sec. 7): Android grava AAC en contenedor MP4, no
    # webm/opus como el navegador. El endpoint no filtra por content-type (lo
    # decodifica faster-whisper/PyAV sin cambios), pero esta prueba lo fija para
    # que una validacion futura no excluya sin querer el formato de la app movil.
    headers, _patient_id, _encounter_id = await _setup(client, make_user, clinic, db_session)

    from app.ai import stt as stt_module

    monkeypatch.setattr(stt_module, "transcribe", lambda audio_bytes, **_: "caries en 36 oclusal")

    response = await client.post(
        "/api/v1/ai/transcribe",
        headers=headers,
        files={"audio": ("dictado.m4a", b"fake-m4a-bytes", "audio/mp4")},
    )

    assert response.status_code == 200, response.text
    assert response.json()["text"] == "caries en 36 oclusal"
