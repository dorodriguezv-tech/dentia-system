"""Fase 13 (Dentia), 13.2 "Navegacion": pruebas del gestor de dialogo con
texto, sin audio -- mismo criterio que el interprete de la Fase 8 (FakeOllama):
"""

import json
import uuid
from datetime import UTC, date, datetime, time, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import ollama_client
from app.ai.models import AiSuggestion
from app.modules.agenda import service as agenda_service
from app.modules.patients.schemas import PatientCreateRequest
from app.modules.patients.service import create_patient
from app.voice import dialogue
from app.voice.context import ScreenContext


def _fake_chat(actions: list[dict], unrecognized: list[dict] | None = None):
    """Mismo patron que tests/integration/ai/test_ai.py -- evita que las
    pruebas de la ruta LLM/dictado (13.5) dependan de un Ollama real."""

    async def _chat(*, model, system_prompt, user_prompt, json_schema, keep_alive=None):
        content = json.dumps({"actions": actions, "unrecognized": unrecognized or []})
        return {"message": {"role": "assistant", "content": content}}

    return _chat


async def _async_none():
    return None


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _headers(token: str, clinic_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic_id)}


async def _make_patient(db_session: AsyncSession, clinic, full_name: tuple[str, str]) -> str:
    patient = await create_patient(
        db_session,
        clinic_id=clinic.id,
        data=PatientCreateRequest(
            first_name=full_name[0], last_name_paternal=full_name[1], date_of_birth="1990-05-20"
        ),
        actor_id=None,
    )
    return str(patient.id)


async def _create_encounter(client: AsyncClient, headers: dict[str, str], patient_id: str) -> str:
    response = await client.post(
        "/api/v1/encounters", headers=headers, json={"patient_id": patient_id}
    )
    return str(response.json()["id"])


async def _make_provider(
    client: AsyncClient,
    make_user,
    clinic,
    db_session: AsyncSession,
    *,
    full_name: str,
    email: str,
) -> str:
    """Admin crea al profesional (misma convencion que test_agenda.py) --
    `make_user` siempre pone "Usuario de prueba" como nombre, asi que se
    sobreescribe para poder probar el emparejamiento por nombre de
    `_find_provider_by_name`."""
    await make_user(email="admin.agenda@example.com", role_code="admin_clinica")
    admin_token = await _login(client, "admin.agenda@example.com")
    admin_headers = _headers(admin_token, clinic.id)

    provider_user = await make_user(email=email, role_code="odontologo")
    provider_user.full_name = full_name
    await db_session.commit()

    response = await client.post(
        "/api/v1/providers", headers=admin_headers, json={"user_id": str(provider_user.id)}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def _create_appointment(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    patient_id: str,
    provider_id: str,
    appointment_type: str,
    starts_at: datetime,
) -> str:
    response = await client.post(
        "/api/v1/appointments",
        headers=headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": appointment_type,
            "starts_at": starts_at.isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def test_ayuda_responds_with_a_summary_and_shows_help_card(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, ayuda",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
    )
    assert "expediente" in result.say.lower()
    assert result.ui_actions[0].action == "show_help"


async def test_repetir_without_a_previous_say_says_nothing_yet(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, repite",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
    )
    assert result.say == "Todavía no he dicho nada."


async def test_repetir_echoes_the_last_say(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, repite",
        context=ScreenContext(),
        last_say="Abriendo expediente de Jose Perez.",
        has_clinical=True,
    )
    assert result.say == "Abriendo expediente de Jose Perez."


async def test_silencio_mutes_and_confirms(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, silencio",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
    )
    assert result.ui_actions[0].action == "mute"


async def test_ir_a_a_standalone_route(client, make_user, clinic, db_session: AsyncSession) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, ve a la agenda",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
    )
    assert result.ui_actions == [dialogue.UiAction("navigate", {"path": "/agenda"})]


async def test_ir_a_a_patient_tab_without_an_active_patient_asks_for_one(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, abre el odontograma",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
    )
    assert "paciente" in result.say.lower()
    assert result.ui_actions == []


async def test_ir_a_a_patient_tab_with_active_patient_navigates_there(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    patient_id = await _make_patient(db_session, clinic, ("Jose", "Perez"))
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, abre el odontograma",
        context=ScreenContext(patient_id=patient_id),
        last_say=None,
        has_clinical=True,
    )
    assert result.ui_actions == [
        dialogue.UiAction("navigate", {"path": f"/pacientes/{patient_id}", "tab": "odontograma"})
    ]


async def test_abrir_expediente_single_match(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, abre el expediente de Juan Perez",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
    )
    assert result.ui_actions == [
        dialogue.UiAction("navigate", {"path": f"/pacientes/{patient_id}"})
    ]
    assert "Juan Perez" in result.say


async def test_abrir_expediente_no_match(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, abre el expediente de Nadie Existente",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
    )
    assert result.ui_actions == []
    assert "no encontré" in result.say.lower()


async def test_abrir_expediente_ambiguous_asks_which_one(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    await _make_patient(db_session, clinic, ("Juan", "Perez"))
    await _make_patient(db_session, clinic, ("Juana", "Perez"))
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, abre el expediente de Perez",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
    )
    assert result.ui_actions == []
    assert "cual" in result.say.lower() or "¿cuál?" in result.say.lower()


async def test_leer_alertas_without_clinical_permission_is_refused(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    """recepcion tiene voice.use pero no voice.clinical (sec. C1 del doc 06)."""
    user = await make_user(email="recepcion@example.com", role_code="recepcion")
    patient_id = await _make_patient(db_session, clinic, ("Jose", "Perez"))
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, ¿tiene alergias?",
        context=ScreenContext(patient_id=patient_id),
        last_say=None,
        has_clinical=False,
    )
    assert "no lo puedo hacer" in result.say.lower()


async def test_leer_alertas_without_an_active_patient_asks_for_one(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, ¿tiene alergias?",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
    )
    assert "paciente" in result.say.lower()


async def test_leer_alertas_reads_the_active_patients_alerts(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)

    patient_id = await _make_patient(db_session, clinic, ("Jose", "Perez"))
    encounter = await client.post(
        "/api/v1/encounters", headers=headers, json={"patient_id": patient_id}
    )
    await client.post(
        f"/api/v1/patients/{patient_id}/allergies",
        headers=headers,
        json={
            "encounter_id": encounter.json()["id"],
            "substance": "Penicilina",
            "severity": "leve",
        },
    )

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, ¿tiene alergias?",
        context=ScreenContext(patient_id=patient_id),
        last_say=None,
        has_clinical=True,
    )
    assert "Penicilina" in result.say


async def test_citas_hoy_without_a_provider_says_so(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="admin@example.com", role_code="admin_clinica")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, ¿qué citas tengo hoy?",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert "agenda propia" in result.say.lower()


async def test_citas_hoy_reports_the_count_and_the_next_one(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    await make_user(email="admin@example.com", role_code="admin_clinica")
    admin_token = await _login(client, "admin@example.com")
    admin_headers = _headers(admin_token, clinic.id)

    odonto = await make_user(email="odonto@example.com", role_code="odontologo")
    provider_resp = await client.post(
        "/api/v1/providers", headers=admin_headers, json={"user_id": str(odonto.id)}
    )
    provider_id = provider_resp.json()["id"]

    patient_id = await _make_patient(db_session, clinic, ("Jose", "Perez"))
    starts_at = datetime.now(UTC) + timedelta(hours=1)
    appt_resp = await client.post(
        "/api/v1/appointments",
        headers=admin_headers,
        json={
            "patient_id": patient_id,
            "provider_id": provider_id,
            "appointment_type": "consulta",
            "starts_at": starts_at.isoformat(),
        },
    )
    assert appt_resp.status_code == 201, appt_resp.text

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=odonto.id,
        transcript="Dentia, ¿qué citas tengo hoy?",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
    )
    assert "Tienes 1 cita hoy" in result.say
    assert "Jose Perez" in result.say


async def test_unrecognized_phrase_asks_to_repeat(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, cuéntame un chiste",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
    )
    assert result.say == "No te entendí, ¿me lo repites?"


async def test_iniciar_consulta_without_an_active_patient_asks_for_one(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, inicia la consulta",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
    )
    assert "paciente" in result.say.lower()
    assert result.pending is None


async def test_iniciar_consulta_without_clinical_permission_is_refused(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="recepcion@example.com", role_code="recepcion")
    patient_id = await _make_patient(db_session, clinic, ("Jose", "Perez"))
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, inicia la consulta",
        context=ScreenContext(patient_id=patient_id),
        last_say=None,
        has_clinical=False,
    )
    assert "no lo puedo hacer" in result.say.lower()


async def test_iniciar_consulta_asks_to_confirm_then_creates_an_encounter(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, inicia la consulta",
        context=ScreenContext(patient_id=patient_id),
        last_say=None,
        has_clinical=True,
    )
    assert "Juan Perez" in result.say
    assert result.pending is not None
    assert result.pending.level == 3
    assert result.pending.confirm_prompt == "¿Confirmas?"

    executed = await result.pending.execute()
    assert executed.say == "Consulta iniciada."
    assert executed.encounter_id is not None


async def test_iniciar_consulta_execute_speaks_active_alerts(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    encounter_id = await _create_encounter(client, headers, patient_id)
    await client.post(
        f"/api/v1/patients/{patient_id}/allergies",
        headers=headers,
        json={"encounter_id": encounter_id, "substance": "Penicilina", "severity": "leve"},
    )

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, inicia la consulta",
        context=ScreenContext(patient_id=patient_id),
        last_say=None,
        has_clinical=True,
    )
    executed = await result.pending.execute()
    assert "Penicilina" in executed.say
    # Ya habia una atencion de hoy (creada arriba via la API): la reutiliza en
    # vez de crear otra (misma idea que useEncounterPicker.ts).
    assert executed.encounter_id == encounter_id


async def test_hallazgo_without_an_active_patient_asks_to_open_one(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, la 18 caries oclusal",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
    )
    assert "paciente" in result.say.lower()
    assert result.pending is None


async def test_hallazgo_without_an_active_encounter_asks_to_start_one(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, la 18 caries oclusal",
        context=ScreenContext(patient_id=patient_id),
        last_say=None,
        has_clinical=True,
        active_encounter_id=None,
    )
    assert "inicia la consulta" in result.say.lower()


async def test_hallazgo_without_clinical_permission_is_refused(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="recepcion@example.com", role_code="recepcion")
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, la 18 caries oclusal",
        context=ScreenContext(patient_id=patient_id),
        last_say=None,
        has_clinical=False,
        active_encounter_id="11111111-1111-1111-1111-111111111111",
    )
    assert "no lo puedo hacer" in result.say.lower()


async def test_hallazgo_missing_a_required_surface_asks_for_it(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    encounter_id = await _create_encounter(client, headers, patient_id)

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, la 18 tiene caries",
        context=ScreenContext(patient_id=patient_id),
        last_say=None,
        has_clinical=True,
        active_encounter_id=encounter_id,
    )
    assert "superficie" in result.say.lower()
    assert result.pending is None


async def test_hallazgo_creates_a_level_2_pending_capture_and_applies_it(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    encounter_id = await _create_encounter(client, headers, patient_id)

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, la 18 caries oclusal y distal",
        context=ScreenContext(patient_id=patient_id),
        last_say=None,
        has_clinical=True,
        active_encounter_id=encounter_id,
    )
    assert result.say == "Coloco caries en la 18, oclusal y distal."
    assert result.pending is not None
    assert result.pending.level == 2
    assert result.pending.confirm_prompt is None

    executed = await result.pending.execute()
    assert executed.say == ""
    assert executed.undo_entry is not None
    assert executed.undo_entry.action_type == "add_tooth_finding"
    assert executed.undo_entry.say == "caries en la 18, oclusal y distal"

    odontogram = await client.get(f"/api/v1/patients/{patient_id}/odontogram", headers=headers)
    findings = odontogram.json()
    assert len(findings) == 2
    assert {f["finding_code"] for f in findings} == {"caries"}
    assert {f["surface"] for f in findings} == {"O", "D"}


async def _give_procedure_catalog_item(
    db_session: AsyncSession, clinic, *, code: str, name: str, actor_id: uuid.UUID
) -> None:
    from decimal import Decimal

    from app.modules.treatment import service as treatment_service
    from app.modules.treatment.schemas import ProcedureCatalogCreateRequest

    await treatment_service.create_procedure_catalog_item(
        db_session,
        clinic_id=clinic.id,
        data=ProcedureCatalogCreateRequest(code=code, name=name, default_price=Decimal("450")),
        actor_id=actor_id,
    )


async def test_diagnostico_without_clinical_permission_is_refused(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="recepcion@example.com", role_code="recepcion")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, diagnóstico: caries profunda",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert "rol" in result.say.lower()
    assert result.pending is None


async def test_diagnostico_without_an_active_encounter_asks_to_start_one(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, diagnóstico: caries profunda",
        context=ScreenContext(patient_id=patient_id),
        last_say=None,
        has_clinical=True,
    )
    assert "consulta" in result.say.lower()
    assert result.pending is None


async def test_diagnostico_creates_a_level_3_pending_capture_and_applies_it(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    encounter_id = await _create_encounter(client, headers, patient_id)

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, pon un diagnóstico de pulpitis reversible en la treinta y seis",
        context=ScreenContext(patient_id=patient_id),
        last_say=None,
        has_clinical=True,
        active_encounter_id=encounter_id,
    )
    assert result.pending is not None
    assert result.pending.level == 3
    assert result.pending.confirm_prompt == "¿Confirmas?"

    executed = await result.pending.execute()
    assert executed.say == "Diagnóstico registrado."

    diagnoses = (
        await client.get(f"/api/v1/patients/{patient_id}/diagnoses", headers=headers)
    ).json()
    assert len(diagnoses) == 1
    assert diagnoses[0]["text"] == "pulpitis reversible en la treinta y seis"
    assert diagnoses[0]["tooth_fdi"] == 36
    assert diagnoses[0]["origin"] == "AI_ASSISTED"


async def test_procedimiento_planeado_without_a_recognized_procedure_says_so(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    encounter_id = await _create_encounter(client, headers, patient_id)

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, planea un procedimiento que no existe",
        context=ScreenContext(patient_id=patient_id),
        last_say=None,
        has_clinical=True,
        active_encounter_id=encounter_id,
    )
    assert "catálogo" in result.say.lower()
    assert result.pending is None


async def test_procedimiento_planeado_creates_a_draft_plan_and_item(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)
    await _give_procedure_catalog_item(
        db_session, clinic, code="resina", name="Resina", actor_id=user.id
    )
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    encounter_id = await _create_encounter(client, headers, patient_id)

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, planea una resina en la 36",
        context=ScreenContext(patient_id=patient_id),
        last_say=None,
        has_clinical=True,
        active_encounter_id=encounter_id,
    )
    assert result.pending is not None
    assert result.pending.level == 3

    executed = await result.pending.execute()
    assert executed.say == "Listo, registrado."

    plans = (
        await client.get(f"/api/v1/patients/{patient_id}/treatment-plans", headers=headers)
    ).json()
    assert len(plans) == 1
    plan_detail = (
        await client.get(f"/api/v1/treatment-plans/{plans[0]['id']}", headers=headers)
    ).json()
    items = [item for phase in plan_detail["phases"] for item in phase["items"]]
    assert len(items) == 1
    assert items[0]["procedure_code"] == "resina"
    assert items[0]["tooth_fdi"] == 36
    assert items[0]["origin"] == "AI_ASSISTED"


async def test_procedimiento_realizado_registers_it(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)
    await _give_procedure_catalog_item(
        db_session, clinic, code="limpieza", name="Limpieza", actor_id=user.id
    )
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    encounter_id = await _create_encounter(client, headers, patient_id)

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, hice una limpieza",
        context=ScreenContext(patient_id=patient_id),
        last_say=None,
        has_clinical=True,
        active_encounter_id=encounter_id,
    )
    assert result.pending is not None

    executed = await result.pending.execute()
    assert executed.say == "Listo, registrado."

    performed = (
        await client.get(f"/api/v1/patients/{patient_id}/procedures-performed", headers=headers)
    ).json()
    assert len(performed) == 1
    assert performed[0]["procedure_code"] == "limpieza"
    assert performed[0]["origin"] == "AI_ASSISTED"


async def test_deshacer_with_nothing_to_undo(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, deshaz",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
        undo_top=None,
    )
    assert result.say == "No hay nada que deshacer."
    assert result.pop_undo is False


async def test_deshacer_a_tooth_finding_retires_it(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    encounter_id = await _create_encounter(client, headers, patient_id)

    caries = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 18,
            "surface": "O",
            "finding_code": "caries",
        },
    )
    undo_top = dialogue.UndoEntry(
        action_type="add_tooth_finding",
        entity_id=caries.json()["id"],
        patient_id=patient_id,
        say="caries en la 18, oclusal",
    )

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, deshaz",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
        undo_top=undo_top,
    )
    assert result.say == "Quité caries en la 18, oclusal."
    assert result.pop_undo is True

    odontogram = await client.get(f"/api/v1/patients/{patient_id}/odontogram", headers=headers)
    assert odontogram.json() == []


async def test_agendar_cita_confirms_and_creates_the_appointment(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """13.4 "Diagnostico, plan y agenda" (C2 del doc 06): recepcion agenda por
    voz sin tener `voice.clinical`."""
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    patient_id = await _make_patient(db_session, clinic, ("Maria", "Lopez"))
    provider_id = await _make_provider(
        client, make_user, clinic, db_session, full_name="Laura Ruiz", email="ruiz@example.com"
    )

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, agenda a Maria Lopez mañana a las 10 con la doctora Ruiz, limpieza",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert "Agendo a Maria Lopez" in result.say
    assert "Laura Ruiz" in result.say
    assert result.pending is not None
    assert result.pending.level == 3
    assert result.pending.confirm_prompt == "¿Confirmas?"

    executed = await result.pending.execute()
    assert "Listo, cita agendada" in executed.say

    tomorrow = date.today() + timedelta(days=1)
    starts_from = datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=UTC)
    appointments = await agenda_service.list_appointments(
        db_session,
        clinic_id=clinic.id,
        starts_from=starts_from,
        starts_to=starts_from + timedelta(days=1),
        provider_id=uuid.UUID(provider_id),
    )
    assert len(appointments) == 1
    assert appointments[0]["patient_id"] == uuid.UUID(patient_id)
    assert appointments[0]["appointment_type"] == "limpieza"
    assert appointments[0]["starts_at"].hour == 10


async def test_agendar_cita_without_a_recognized_provider_asks_for_one(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    await _make_patient(db_session, clinic, ("Maria", "Lopez"))

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, agenda a Maria Lopez mañana a las 10 con el doctor Nadie, limpieza",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert "profesional" in result.say.lower()
    assert result.pending is None


async def test_agendar_cita_conflict_is_reported_gracefully(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    token = await _login(client, "recepcion@example.com")
    headers = _headers(token, clinic.id)
    await _make_patient(db_session, clinic, ("Maria", "Lopez"))
    other_patient_id = await _make_patient(db_session, clinic, ("Pedro", "Gomez"))
    provider_id = await _make_provider(
        client, make_user, clinic, db_session, full_name="Laura Ruiz", email="ruiz@example.com"
    )

    tomorrow = date.today() + timedelta(days=1)
    busy_starts_at = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 10, 0, tzinfo=UTC)
    await _create_appointment(
        client,
        headers,
        patient_id=other_patient_id,
        provider_id=provider_id,
        appointment_type="limpieza",
        starts_at=busy_starts_at,
    )

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, agenda a Maria Lopez mañana a las 10 con la doctora Ruiz, limpieza",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert result.pending is not None
    executed = await result.pending.execute()
    assert "ocupado" in executed.say.lower()


async def test_confirmar_cita_by_patient_name_changes_status(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    token = await _login(client, "recepcion@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Maria", "Lopez"))
    provider_id = await _make_provider(
        client, make_user, clinic, db_session, full_name="Laura Ruiz", email="ruiz@example.com"
    )
    today = date.today()
    starts_at = datetime(today.year, today.month, today.day, 10, 0, tzinfo=UTC)
    appointment_id = await _create_appointment(
        client,
        headers,
        patient_id=patient_id,
        provider_id=provider_id,
        appointment_type="limpieza",
        starts_at=starts_at,
    )

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, confirma la cita de Maria Lopez",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert result.pending is not None
    assert result.pending.level == 2
    executed = await result.pending.execute()
    assert executed.say == ""

    appointments = await agenda_service.list_appointments(
        db_session,
        clinic_id=clinic.id,
        starts_from=datetime(today.year, today.month, today.day, tzinfo=UTC),
        starts_to=datetime(today.year, today.month, today.day, 23, 59, tzinfo=UTC),
    )
    assert appointments[0]["status"] == "CONFIRMADA"
    assert appointments[0]["id"] == uuid.UUID(appointment_id)


async def test_registrar_llegada_changes_status_to_en_sala(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    token = await _login(client, "recepcion@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Maria", "Lopez"))
    provider_id = await _make_provider(
        client, make_user, clinic, db_session, full_name="Laura Ruiz", email="ruiz@example.com"
    )
    today = date.today()
    starts_at = datetime(today.year, today.month, today.day, 10, 0, tzinfo=UTC)
    await _create_appointment(
        client,
        headers,
        patient_id=patient_id,
        provider_id=provider_id,
        appointment_type="limpieza",
        starts_at=starts_at,
    )

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, llegó Maria Lopez",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert result.pending is not None
    executed = await result.pending.execute()
    assert executed.say == ""

    appointments = await agenda_service.list_appointments(
        db_session,
        clinic_id=clinic.id,
        starts_from=datetime(today.year, today.month, today.day, tzinfo=UTC),
        starts_to=datetime(today.year, today.month, today.day, 23, 59, tzinfo=UTC),
    )
    assert appointments[0]["status"] == "EN_SALA"


async def test_reprogramar_cita_moves_the_appointment_keeping_the_time(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    token = await _login(client, "recepcion@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Maria", "Lopez"))
    provider_id = await _make_provider(
        client, make_user, clinic, db_session, full_name="Laura Ruiz", email="ruiz@example.com"
    )
    today = date.today()
    starts_at = datetime(today.year, today.month, today.day, 10, 0, tzinfo=UTC)
    await _create_appointment(
        client,
        headers,
        patient_id=patient_id,
        provider_id=provider_id,
        appointment_type="limpieza",
        starts_at=starts_at,
    )

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, mueve la cita de Maria Lopez al viernes",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert result.pending is not None
    assert result.pending.level == 3
    executed = await result.pending.execute()
    assert executed.say == "Listo, cita reprogramada."

    friday = today + timedelta(days=(4 - today.weekday()) % 7)
    appointments = await agenda_service.list_appointments(
        db_session,
        clinic_id=clinic.id,
        starts_from=datetime(friday.year, friday.month, friday.day, tzinfo=UTC),
        starts_to=datetime(friday.year, friday.month, friday.day, 23, 59, tzinfo=UTC),
    )
    # reschedule_appointment nunca muta la cita en el lugar (regla 2 de
    # CLAUDE.md): marca la vieja como REPROGRAMADA y crea una fila nueva en
    # RESERVADA. "al viernes" cuando hoy mismo ya es viernes (datetime_parse.py:
    # "si hoy mismo es ese dia, es hoy", deliberado) hace que la cita vieja
    # tambien caiga en el rango de este query -- no se filtra list_appointments
    # por status a proposito (el calendario real muestra "Reprogramada" en su
    # lugar original en vez de ocultarla, agenda/catalog.ts), asi que no hay
    # que asumir cuantas filas hay en total, solo que la nueva (RESERVADA) esta
    # y que ninguna otra fila del mismo paciente quedo mutada en el lugar.
    reserved = [a for a in appointments if a["status"] == "RESERVADA"]
    assert len(reserved) == 1
    assert reserved[0]["starts_at"].hour == 10
    assert reserved[0]["patient_id"] == uuid.UUID(patient_id)
    others = [a for a in appointments if a["id"] != reserved[0]["id"]]
    assert all(a["status"] != "RESERVADA" for a in others)


async def test_reprogramar_cita_without_a_matching_appointment_says_so(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, mueve la cita de Nadie Existe al viernes",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert "no encontré" in result.say.lower()
    assert result.pending is None


async def test_modo_dictado_without_an_active_encounter_asks_to_start_one(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, dictado",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
    )
    assert "inicia la consulta" in result.say.lower()
    assert result.start_dictation is False


async def test_modo_dictado_without_clinical_permission_is_refused(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="recepcion@example.com", role_code="recepcion")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, dictado",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
        active_encounter_id="11111111-1111-1111-1111-111111111111",
    )
    assert "no lo puedo hacer" in result.say.lower()


async def test_modo_dictado_starts_dictation(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    encounter_id = await _create_encounter(client, headers, patient_id)

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, dictado",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
        active_encounter_id=encounter_id,
    )
    assert result.start_dictation is True
    assert "dictado" in result.say.lower()


async def test_finish_dictation_with_empty_transcript_says_so(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    encounter_id = await _create_encounter(client, headers, patient_id)

    result = await dialogue.finish_dictation(
        db_session, clinic_id=clinic.id, user_id=user.id, encounter_id=encounter_id, transcript="  "
    )
    assert result.say == "No dictaste nada."
    assert result.pending is None


async def test_finish_dictation_with_no_recognized_actions_says_so(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    encounter_id = await _create_encounter(client, headers, patient_id)

    monkeypatch.setattr(ollama_client, "chat", _fake_chat([]))
    monkeypatch.setattr(ollama_client, "model_digest", lambda model: _async_none())

    result = await dialogue.finish_dictation(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        encounter_id=encounter_id,
        transcript="cuéntame un chiste sobre muelas",
    )
    assert "no entendí" in result.say.lower()
    assert result.pending is None


async def test_finish_dictation_confirms_and_accepts_all_suggestions(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    """Flujo de "Dentia, dictado" ... "fin del dictado" del diseno (sec. 4.2):
    "Tengo N propuestas, ¿las acepto todas?" -- reusa el interprete de la
    Fase 8 (texto -> AiSuggestion vía Ollama), no un esquema de voz aparte."""
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    encounter_id = await _create_encounter(client, headers, patient_id)

    monkeypatch.setattr(
        ollama_client,
        "chat",
        _fake_chat(
            [
                {"type": "add_allergy", "substance": "Penicilina"},
                {"type": "set_chief_complaint", "text": "Dolor en la muela 36"},
            ]
        ),
    )
    monkeypatch.setattr(ollama_client, "model_digest", lambda model: _async_none())

    result = await dialogue.finish_dictation(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        encounter_id=encounter_id,
        transcript="alérgica a la penicilina, dolor en la muela 36",
    )
    assert result.say == "Tengo 2 propuestas. ¿Las acepto todas?"
    assert result.pending is not None
    assert result.pending.level == 3

    executed = await result.pending.execute()
    assert executed.say == "Listo, aplicadas."

    accepted = (
        (
            await db_session.execute(
                select(AiSuggestion).where(AiSuggestion.encounter_id == uuid.UUID(encounter_id))
            )
        )
        .scalars()
        .all()
    )
    assert len(accepted) == 2
    assert all(s.status == "ACCEPTED" for s in accepted)


async def test_finish_dictation_cancel_leaves_suggestions_pending(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    encounter_id = await _create_encounter(client, headers, patient_id)

    monkeypatch.setattr(
        ollama_client, "chat", _fake_chat([{"type": "add_allergy", "substance": "Penicilina"}])
    )
    monkeypatch.setattr(ollama_client, "model_digest", lambda model: _async_none())

    result = await dialogue.finish_dictation(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        encounter_id=encounter_id,
        transcript="alérgica a la penicilina",
    )
    assert result.pending is not None
    assert result.pending.cancel_say == "Quedan pendientes en el panel de propuestas."

    pending = (
        (
            await db_session.execute(
                select(AiSuggestion).where(AiSuggestion.encounter_id == uuid.UUID(encounter_id))
            )
        )
        .scalars()
        .all()
    )
    assert len(pending) == 1
    assert pending[0].status == "PENDING"


async def test_unrecognized_with_an_active_encounter_tries_the_llm_route(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    """13.5, sec. 5 del diseno: una orden suelta que la ruta rapida no
    reconoce intenta la ruta LLM antes de rendirse -- nivel 3 siempre (baja
    certeza), reusa el mismo AiSuggestion+applier que las demas capturas."""
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    encounter_id = await _create_encounter(client, headers, patient_id)

    monkeypatch.setattr(
        ollama_client,
        "chat",
        _fake_chat([{"type": "add_allergy", "substance": "Penicilina"}]),
    )
    monkeypatch.setattr(ollama_client, "model_digest", lambda model: _async_none())

    # Una frase que ninguna ruta rapida reconoce (ni agenda, ni hallazgo, ni
    # diagnostico/procedimiento -- esos ya tienen su propio camino
    # deterministico desde el resto de 13.4): cae a la ruta LLM de la 13.5.
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, la paciente me dice que es alérgica a la penicilina",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
        active_encounter_id=encounter_id,
    )
    assert result.say == "Registro una alergia: Penicilina."
    assert result.pending is not None
    assert result.pending.level == 3
    assert result.pending.confirm_prompt == "¿Confirmas?"

    executed = await result.pending.execute()
    assert executed.say == "Listo."

    created = (
        (
            await db_session.execute(
                select(AiSuggestion).where(AiSuggestion.encounter_id == uuid.UUID(encounter_id))
            )
        )
        .scalars()
        .all()
    )
    assert len(created) == 1
    assert created[0].status == "ACCEPTED"
    assert created[0].action_type == "add_allergy"


async def test_unrecognized_llm_route_with_multiple_actions_falls_back(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    """Mas de una accion es dictado (modo_dictado), no una orden suelta --
    la ruta LLM de 13.5 solo aplica a UNA orden a la vez."""
    user = await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Juan", "Perez"))
    encounter_id = await _create_encounter(client, headers, patient_id)

    monkeypatch.setattr(
        ollama_client,
        "chat",
        _fake_chat(
            [
                {"type": "add_allergy", "substance": "Penicilina"},
                {"type": "set_chief_complaint", "text": "Dolor"},
            ]
        ),
    )
    monkeypatch.setattr(ollama_client, "model_digest", lambda model: _async_none())

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, cuéntame algo que la ruta rápida no reconozca",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
        active_encounter_id=encounter_id,
    )
    assert result.say == "No te entendí, ¿me lo repites?"
    assert result.pending is None


async def test_unrecognized_without_an_active_encounter_skips_the_clinical_llm_route(
    client, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    """Sin atencion activa, `_try_llm_fallback` (clinico) ni se intenta -- pero
    la ruta LLM de AGENDA (resto de 13.5) si, porque no exige atencion activa
    ni `voice.clinical` (sec. C2 del doc 06, igual que la agenda de la ruta
    rapida): `chat()` SI se llama una vez, para esa, y como no devuelve
    ninguna accion de agenda reconocida, cae igual en "no te entendi"."""
    user = await make_user(email="odonto@example.com", role_code="odontologo")

    calls = 0

    async def _chat(**_kwargs):
        nonlocal calls
        calls += 1
        return {"message": {"role": "assistant", "content": "{}"}}

    monkeypatch.setattr(ollama_client, "chat", _chat)

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=user.id,
        transcript="Dentia, cuéntame un chiste",
        context=ScreenContext(),
        last_say=None,
        has_clinical=True,
    )
    assert result.say == "No te entendí, ¿me lo repites?"
    assert calls == 1


def _fake_agenda_chat(action: dict | None):
    """Mismo patron que `_fake_chat` (ruta LLM clinica) pero con la forma de
    `agenda_llm.AgendaInterpretResult` ({"action": ...}), no la de
    `AiInterpretResult` ({"actions": [...], "unrecognized": [...]})."""

    async def _chat(*, model, system_prompt, user_prompt, json_schema, keep_alive=None):
        content = json.dumps({"action": action})
        return {"message": {"role": "assistant", "content": content}}

    return _chat


async def test_agenda_llm_fallback_agenda_cita_with_free_phrasing(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    """Resto de 13.5: una frase de agenda que `nlu_fast` no reconoce (no trae
    las anclas "a las"/"con") se resuelve igual via la ruta LLM de agenda --
    disponible para recepcion, sin atencion activa ni `voice.clinical`."""
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    await _make_patient(db_session, clinic, ("Maria", "Lopez"))
    provider_id = await _make_provider(
        client, make_user, clinic, db_session, full_name="Laura Ruiz", email="ruiz@example.com"
    )
    monkeypatch.setattr(
        ollama_client,
        "chat",
        _fake_agenda_chat(
            {
                "type": "agendar_cita",
                "patient_name": "Maria Lopez",
                "provider_name": "Ruiz",
                "date_text": "manana",
                "time_text": "10",
                "appointment_type_hint": "limpieza",
            }
        ),
    )

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, el jueves que viene necesito un espacio para Maria Lopez",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert result.pending is not None
    assert result.pending.level == 3
    assert "Maria Lopez" in result.say
    assert "Laura Ruiz" in result.say

    executed = await result.pending.execute()
    assert "Listo, cita agendada" in executed.say

    tomorrow = date.today() + timedelta(days=1)
    starts_from = datetime(tomorrow.year, tomorrow.month, tomorrow.day, tzinfo=UTC)
    appointments = await agenda_service.list_appointments(
        db_session,
        clinic_id=clinic.id,
        starts_from=starts_from,
        starts_to=starts_from + timedelta(days=1),
        provider_id=uuid.UUID(provider_id),
    )
    assert len(appointments) == 1
    assert appointments[0]["appointment_type"] == "limpieza"
    assert appointments[0]["starts_at"].hour == 10


async def test_agenda_llm_fallback_with_no_recognized_action_falls_to_unrecognized(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    monkeypatch.setattr(ollama_client, "chat", _fake_agenda_chat(None))

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, cuéntame un chiste",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert result.say == "No te entendí, ¿me lo repites?"


async def test_agenda_llm_fallback_cancelar_cita_without_a_reason_is_not_recognized(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    """El esquema de `agenda_llm.py` exige `reason` para "cancelar_cita" -- si
    Ollama no lo manda, la validacion de Pydantic falla y se trata igual que
    "no reconoci nada" (mismo criterio que la ruta rapida, #43)."""
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    monkeypatch.setattr(
        ollama_client,
        "chat",
        _fake_agenda_chat({"type": "cancelar_cita", "patient_name": "Maria Lopez"}),
    )

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, ya no va a venir Maria Lopez",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert result.say == "No te entendí, ¿me lo repites?"


async def test_agenda_llm_fallback_lista_espera_pronoun_uses_the_last_patient(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession, monkeypatch
) -> None:
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    patient_id = await _make_patient(db_session, clinic, ("Maria", "Lopez"))
    monkeypatch.setattr(
        ollama_client, "chat", _fake_agenda_chat({"type": "lista_espera", "patient_name": None})
    )

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, ponla tambien en la lista de espera porfavor",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
        last_patient=(patient_id, "Maria Lopez"),
    )
    assert result.pending is not None
    executed = await result.pending.execute()
    assert "espera" in executed.say.lower()

    waitlist = await agenda_service.list_waitlist(db_session, clinic_id=clinic.id)
    assert len(waitlist) == 1
    assert waitlist[0].patient_id == uuid.UUID(patient_id)


# ----------------------------------- 13.4 (resto): huecos, cancelar/no_show,
# ----------------------------------- lista de espera, alta rapida de paciente


async def _give_working_hours(
    db_session: AsyncSession,
    clinic_id,
    provider_id: str,
    *,
    day: date,
    start_hour: int,
    end_hour: int,
) -> None:
    from app.modules.agenda.schemas import WorkingHoursCreateRequest

    await agenda_service.create_working_hours(
        db_session,
        clinic_id=clinic_id,
        provider_id=uuid.UUID(provider_id),
        data=WorkingHoursCreateRequest(
            weekday=day.weekday(), start_time=time(start_hour, 0), end_time=time(end_hour, 0)
        ),
    )


async def test_huecos_libres_proposes_real_free_slots(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    provider_id = await _make_provider(
        client, make_user, clinic, db_session, full_name="Laura Ruiz", email="ruiz@example.com"
    )
    tomorrow = date.today() + timedelta(days=1)
    await _give_working_hours(
        db_session, clinic.id, provider_id, day=tomorrow, start_hour=9, end_hour=10
    )

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, cuándo hay espacio con la doctora Ruiz mañana",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert result.pending is None
    assert "09:00" in result.say
    assert "Laura Ruiz" in result.say


async def test_huecos_libres_without_a_recognized_provider_asks_for_one(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, qué horarios libres hay con el doctor Nadie",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert "profesional" in result.say.lower()


async def test_agendar_cita_without_a_time_proposes_free_slots(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    await _make_patient(db_session, clinic, ("Maria", "Lopez"))
    provider_id = await _make_provider(
        client, make_user, clinic, db_session, full_name="Laura Ruiz", email="ruiz@example.com"
    )
    tomorrow = date.today() + timedelta(days=1)
    await _give_working_hours(
        db_session, clinic.id, provider_id, day=tomorrow, start_hour=9, end_hour=10
    )

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, agenda a Maria Lopez mañana con la doctora Ruiz, limpieza",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert result.pending is None
    assert "09:00" in result.say
    assert "Laura Ruiz" in result.say


async def test_cancelar_cita_without_a_reason_asks_for_one(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, cancela la cita de Maria Lopez",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert "motivo" in result.say.lower()
    assert result.pending is None


async def test_cancelar_cita_by_time_with_reason_changes_status(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    token = await _login(client, "recepcion@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Maria", "Lopez"))
    provider_id = await _make_provider(
        client, make_user, clinic, db_session, full_name="Laura Ruiz", email="ruiz@example.com"
    )
    today = date.today()
    starts_at = datetime(today.year, today.month, today.day, 12, 0, tzinfo=UTC)
    appointment_id = await _create_appointment(
        client,
        headers,
        patient_id=patient_id,
        provider_id=provider_id,
        appointment_type="limpieza",
        starts_at=starts_at,
    )

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, cancela la cita de las 12, motivo: enfermedad",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert result.pending is not None
    assert result.pending.level == 3
    assert result.patient_ref == (patient_id, "Maria Lopez")
    executed = await result.pending.execute()
    assert "cancelada" in executed.say.lower()

    appointments = await agenda_service.list_appointments(
        db_session,
        clinic_id=clinic.id,
        starts_from=datetime(today.year, today.month, today.day, tzinfo=UTC),
        starts_to=datetime(today.year, today.month, today.day, 23, 59, tzinfo=UTC),
    )
    assert appointments[0]["id"] == uuid.UUID(appointment_id)
    assert appointments[0]["status"] == "CANCELADA"


async def test_no_show_suffix_phrasing_changes_status(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    token = await _login(client, "recepcion@example.com")
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, ("Maria", "Lopez"))
    provider_id = await _make_provider(
        client, make_user, clinic, db_session, full_name="Laura Ruiz", email="ruiz@example.com"
    )
    today = date.today()
    starts_at = datetime(today.year, today.month, today.day, 10, 0, tzinfo=UTC)
    await _create_appointment(
        client,
        headers,
        patient_id=patient_id,
        provider_id=provider_id,
        appointment_type="limpieza",
        starts_at=starts_at,
    )

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, Maria Lopez no llegó",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert result.pending is not None
    executed = await result.pending.execute()
    assert "registrado" in executed.say.lower()

    appointments = await agenda_service.list_appointments(
        db_session,
        clinic_id=clinic.id,
        starts_from=datetime(today.year, today.month, today.day, tzinfo=UTC),
        starts_to=datetime(today.year, today.month, today.day, 23, 59, tzinfo=UTC),
    )
    assert appointments[0]["status"] == "NO_SHOW"


async def test_lista_espera_with_explicit_name_creates_entry(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    patient_id = await _make_patient(db_session, clinic, ("Maria", "Lopez"))

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, agrega a Maria Lopez a la lista de espera",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert result.pending is not None
    assert result.pending.level == 2
    executed = await result.pending.execute()
    assert "espera" in executed.say.lower()

    waitlist = await agenda_service.list_waitlist(db_session, clinic_id=clinic.id)
    assert len(waitlist) == 1
    assert waitlist[0].patient_id == uuid.UUID(patient_id)


async def test_lista_espera_pronoun_uses_the_last_resolved_patient(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    patient_id = await _make_patient(db_session, clinic, ("Maria", "Lopez"))

    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, agrégala a la lista de espera",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
        last_patient=(patient_id, "Maria Lopez"),
    )
    assert result.pending is not None
    executed = await result.pending.execute()
    assert "espera" in executed.say.lower()

    waitlist = await agenda_service.list_waitlist(db_session, clinic_id=clinic.id)
    assert len(waitlist) == 1
    assert waitlist[0].patient_id == uuid.UUID(patient_id)


async def test_lista_espera_pronoun_without_a_last_patient_asks_for_one(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    recepcion = await make_user(email="recepcion@example.com", role_code="recepcion")
    result = await dialogue.handle_order(
        db_session,
        clinic_id=clinic.id,
        user_id=recepcion.id,
        transcript="Dentia, agrégala a la lista de espera",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert "paciente" in result.say.lower()
    assert result.pending is None


async def test_alta_rapida_paciente_opens_the_prefilled_form() -> None:
    result = await dialogue.handle_order(
        None,  # type: ignore[arg-type]
        clinic_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        transcript="Dentia, registra paciente nuevo Pedro Sanchez, telefono 555 123 4567",
        context=ScreenContext(),
        last_say=None,
        has_clinical=False,
    )
    assert result.pending is None
    assert "Pedro Sanchez" in result.say
    assert len(result.ui_actions) == 1
    action = result.ui_actions[0]
    assert action.action == "navigate"
    path = action.payload["path"]
    assert path.startswith("/pacientes/nuevo?")
    assert "first_name=Pedro" in path
    assert "last_name_paternal=Sanchez" in path
    assert "phone=5551234567" in path
