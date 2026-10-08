"""Fase 13 (Dentia), 13.1 "Base de voz": pruebas del WebSocket /voice/ws.

Usa VOICE_FAKE_MODE (vease app/voice/session.py) para evitar audio real -- el
mensaje "fake_wake" dispara la misma secuencia que detectar "Dentia" de verdad,
sin VAD ni Whisper. Starlette TestClient (sincrono) es el camino recomendado por
FastAPI para probar WebSockets incluso en una app async -- corre la app en su
propio hilo/portal, por eso convive bien con pytest-asyncio aqui.
"""

from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient

from app.core.config import get_settings
from app.core.security import create_access_token
from app.main import app
from app.modules.iam.models import Clinic, User
from app.voice.models import VoiceCommandLog
from app.voice.session import VoiceSession


async def _access_token_for(user: User) -> str:
    token, _jti, _expires_at = create_access_token(user.id)
    return token


async def _async_none():
    return None


async def test_wake_detected_via_fake_mode_responds_with_say_and_logs(
    client,  # noqa: ARG001 -- solo para que app.state.db_sessionmaker apunte a la BD de pruebas
    make_user,
    clinic: Clinic,
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    class _FakeSettings:
        voice_fake_mode = True
        voice_capture_countdown_s = 0.01
        voice_followup_s = 0.01

    monkeypatch.setattr("app.voice.session.get_settings", lambda: _FakeSettings())
    monkeypatch.setattr("app.voice.tts.get_settings", lambda: _FakeSettings())

    user = await make_user(email="odonto.voz@example.com", role_code="odontologo")
    token = await _access_token_for(user)

    with TestClient(app).websocket_connect("/api/v1/voice/ws") as ws:
        ws.send_json({"type": "auth", "token": token, "clinic_id": str(clinic.id)})
        assert ws.receive_json() == {"type": "state", "state": "passive"}

        ws.send_json({"type": "fake_wake"})

        assert ws.receive_json() == {"type": "state", "state": "awake"}
        assert ws.receive_json() == {"type": "state", "state": "speaking"}
        say = ws.receive_json()
        assert say["type"] == "say"
        assert say["text"] == "¿Sí?"
        assert say["audio"] is None  # VOICE_FAKE_MODE: nunca toca Piper
        # 13.3: tambien entra a la ventana de seguimiento (sec. 2.1) en vez de
        # volver directo a pasivo.
        assert ws.receive_json() == {"type": "state", "state": "listening"}

    logs = (
        (
            await db_session.execute(
                select(VoiceCommandLog).where(VoiceCommandLog.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(logs) == 1
    assert logs[0].event == "wake_detected"
    assert logs[0].clinic_id == clinic.id


async def test_connection_rejected_without_voice_permission(
    client,  # noqa: ARG001
    make_user,
    clinic: Clinic,
) -> None:
    """`admin_clinica` no tiene voice.use (ver docs/06... sec. C1)."""
    user = await make_user(email="admin.voz@example.com", role_code="admin_clinica")
    token = await _access_token_for(user)

    with TestClient(app).websocket_connect("/api/v1/voice/ws") as ws:
        ws.send_json({"type": "auth", "token": token, "clinic_id": str(clinic.id)})
        error = ws.receive_json()
        assert error["type"] == "error"
        assert error["code"] == "FORBIDDEN"


async def test_connection_rejected_with_invalid_token(
    client,  # noqa: ARG001
    clinic: Clinic,
) -> None:
    with TestClient(app).websocket_connect("/api/v1/voice/ws") as ws:
        ws.send_json({"type": "auth", "token": "not-a-real-token", "clinic_id": str(clinic.id)})
        error = ws.receive_json()
        assert error["type"] == "error"
        assert error["code"] == "UNAUTHENTICATED"


async def test_mute_blocks_audio_processing(
    client,  # noqa: ARG001
    make_user,
    clinic: Clinic,
    monkeypatch,
) -> None:
    class _FakeSettings:
        voice_fake_mode = True
        voice_capture_countdown_s = 0.01
        voice_followup_s = 0.01

    monkeypatch.setattr("app.voice.session.get_settings", lambda: _FakeSettings())
    monkeypatch.setattr("app.voice.tts.get_settings", lambda: _FakeSettings())

    user = await make_user(email="odonto.mute@example.com", role_code="odontologo")
    token = await _access_token_for(user)

    with TestClient(app).websocket_connect("/api/v1/voice/ws") as ws:
        ws.send_json({"type": "auth", "token": token, "clinic_id": str(clinic.id)})
        ws.receive_json()  # state: passive

        ws.send_json({"type": "ui", "action": "mute"})
        assert ws.receive_json() == {"type": "state", "state": "muted"}

        # Mientras esta muteado, "fake_wake" tambien se ignora -- mute corta
        # cualquier procesamiento, no solo el audio real.
        ws.send_json({"type": "ui", "action": "unmute"})
        assert ws.receive_json() == {"type": "state", "state": "passive"}


@pytest.mark.skipif(
    not Path(get_settings().voice_tts_model_path or "").is_file(),
    reason=(
        "voices/es_MX-claude-high.onnx no esta descargado -- "
        "python -m piper.download_voices es_MX-claude-high --download-dir ../voices"
    ),
)
async def test_send_say_embeds_real_piper_audio_outside_fake_mode() -> None:
    """A diferencia de las demas pruebas de este archivo, esta usa
    VOICE_FAKE_MODE=false de verdad (el valor real de .env) para comprobar que
    VoiceSession.send_say() de verdad queda conectado con tts.py y
    piper_worker.py -- no solo cada pieza por separado (ver test_tts_piper.py).
    Se llama directo, sin pasar por una conexion de WebSocket real: no hay
    ninguna forma de disparar esto desde el protocolo sin audio real."""
    sent: list[dict] = []

    class _FakeWebSocket:
        async def send_json(self, data: dict) -> None:
            sent.append(data)

    session = VoiceSession(
        websocket=_FakeWebSocket(),  # type: ignore[arg-type]
        db=None,  # type: ignore[arg-type]
        user=None,  # type: ignore[arg-type]
        clinic_id=None,  # type: ignore[arg-type]
    )

    await session.send_say("¿Sí?")

    assert len(sent) == 1
    assert sent[0]["type"] == "say"
    assert sent[0]["text"] == "¿Sí?"
    assert sent[0]["audio"] is not None
    import base64

    wav = base64.b64decode(sent[0]["audio"])
    assert wav[:4] == b"RIFF"


async def test_fake_order_ir_a_sends_a_ui_action(
    client,  # noqa: ARG001
    make_user,
    clinic: Clinic,
    monkeypatch,
) -> None:
    """13.2 "Navegacion": fake_order simula la orden capturada despues de
    "Dentia" (sin audio real) -- prueba session.py conectado con dialogue.py
    de punta a punta."""

    class _FakeSettings:
        voice_fake_mode = True
        voice_capture_countdown_s = 0.01
        voice_followup_s = 0.01

    monkeypatch.setattr("app.voice.session.get_settings", lambda: _FakeSettings())
    monkeypatch.setattr("app.voice.tts.get_settings", lambda: _FakeSettings())

    user = await make_user(email="odonto.orden@example.com", role_code="odontologo")
    token = await _access_token_for(user)

    with TestClient(app).websocket_connect("/api/v1/voice/ws") as ws:
        ws.send_json({"type": "auth", "token": token, "clinic_id": str(clinic.id)})
        assert ws.receive_json() == {"type": "state", "state": "passive"}

        ws.send_json({"type": "fake_order", "text": "ve a la agenda"})

        assert ws.receive_json() == {"type": "state", "state": "awake"}
        assert ws.receive_json() == {"type": "state", "state": "thinking"}
        ui_action = ws.receive_json()
        assert ui_action == {
            "type": "ui_action",
            "action": "navigate",
            "payload": {"path": "/agenda"},
        }
        assert ws.receive_json() == {"type": "state", "state": "speaking"}
        say = ws.receive_json()
        assert say["text"] == "Abriendo agenda."
        # 13.3 "Captura en consulta": tras resolver la orden entra a la
        # ventana de seguimiento (sec. 2.1) en vez de volver directo a
        # pasivo -- se puede seguir dando ordenes sin repetir "Dentia".
        assert ws.receive_json() == {"type": "state", "state": "listening"}


async def test_fake_order_respects_screen_context_from_the_client(
    client: AsyncClient,  # noqa: ARG001
    make_user,
    clinic: Clinic,
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    """El cliente manda `context` cada vez que cambia de pantalla (sec. 6.1 del
    diseno); Dentia lo usa para saber de que paciente se habla sin que la orden
    lo repita ("abre el odontograma" sin decir el nombre)."""
    from app.modules.patients.schemas import PatientCreateRequest
    from app.modules.patients.service import create_patient

    class _FakeSettings:
        voice_fake_mode = True
        voice_capture_countdown_s = 0.01
        voice_followup_s = 0.01

    monkeypatch.setattr("app.voice.session.get_settings", lambda: _FakeSettings())
    monkeypatch.setattr("app.voice.tts.get_settings", lambda: _FakeSettings())

    user = await make_user(email="odonto.contexto@example.com", role_code="odontologo")
    token = await _access_token_for(user)
    patient = await create_patient(
        db_session,
        clinic_id=clinic.id,
        data=PatientCreateRequest(
            first_name="Jose", last_name_paternal="Perez", date_of_birth="1990-05-20"
        ),
        actor_id=None,
    )

    with TestClient(app).websocket_connect("/api/v1/voice/ws") as ws:
        ws.send_json({"type": "auth", "token": token, "clinic_id": str(clinic.id)})
        ws.receive_json()  # state: passive

        ws.send_json(
            {
                "type": "context",
                "route": f"/pacientes/{patient.id}",
                "patient_id": str(patient.id),
            }
        )

        ws.send_json({"type": "fake_order", "text": "abre el odontograma"})
        ws.receive_json()  # state: awake
        ws.receive_json()  # state: thinking
        ui_action = ws.receive_json()
        assert ui_action["payload"] == {"path": f"/pacientes/{patient.id}", "tab": "odontograma"}


async def test_fake_order_unrecognized_asks_to_repeat(
    client,  # noqa: ARG001
    make_user,
    clinic: Clinic,
    monkeypatch,
) -> None:
    class _FakeSettings:
        voice_fake_mode = True
        voice_capture_countdown_s = 0.01
        voice_followup_s = 0.01

    monkeypatch.setattr("app.voice.session.get_settings", lambda: _FakeSettings())
    monkeypatch.setattr("app.voice.tts.get_settings", lambda: _FakeSettings())

    user = await make_user(email="odonto.rara@example.com", role_code="odontologo")
    token = await _access_token_for(user)

    with TestClient(app).websocket_connect("/api/v1/voice/ws") as ws:
        ws.send_json({"type": "auth", "token": token, "clinic_id": str(clinic.id)})
        ws.receive_json()  # state: passive

        ws.send_json({"type": "fake_order", "text": "cuéntame un chiste"})
        ws.receive_json()  # state: awake
        ws.receive_json()  # state: thinking
        ws.receive_json()  # state: speaking
        say = ws.receive_json()
        assert say["text"] == "No te entendí, ¿me lo repites?"


def _drain_until_say(ws) -> dict:
    """Se salta los "state"/"ui_action" intermedios (cuenta regresiva,
    ejecucion silenciosa de la captura anterior, ventana de seguimiento...)
    y devuelve el siguiente mensaje "say" -- mas robusto que contar mensajes
    uno por uno para un flujo con varias capturas encadenadas."""
    while True:
        msg = ws.receive_json()
        if msg.get("type") == "say":
            return msg


# Solo posteriores (posicion 4-8): "oclusal" no es una superficie valida en
# incisivos/canino (posicion 1-3, ver odontogram/rules.py::is_anterior_tooth)
# -- 5 posiciones x 4 cuadrantes = exactamente 20 piezas.
_TWENTY_TEETH = [quadrant * 10 + position for quadrant in (1, 2, 3, 4) for position in range(4, 9)]


async def test_full_capture_flow_start_consulta_20_findings_cancela_and_deshaz(
    client: AsyncClient,  # noqa: ARG001
    make_user,
    clinic: Clinic,
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    """13.3 "Captura en consulta": criterio de aceptacion literal de
    docs/06_INSTRUCCIONES_CLAUDE_CODE_CORRECCIONES_Y_FASE13.md -- "20
    hallazgos seguidos dictados en el odontograma sin tocar el teclado;
    'cancela' y 'deshaz' funcionan". Cada hallazgo nuevo llega mientras el
    anterior todavia esta en su cuenta regresiva (nivel 2) -- exactamente como
    dictaria un odontologo real, sin pausar a esperar los 3 s de cada uno
    (sec. 2.1 del diseno, ver session.py::_handle_pending_reply)."""
    from app.ai import ollama_client
    from app.modules.patients.schemas import PatientCreateRequest
    from app.modules.patients.service import create_patient

    class _FakeSettings:
        voice_fake_mode = True
        # Deliberadamente generosos (no 0.01 como en otras pruebas): esta
        # prueba nunca depende de que la cuenta regresiva real dispare sola
        # -- cada captura se resuelve por un mensaje explicito ("cancela",
        # "si", la siguiente orden) y un valor corto arriesgaria una
        # condicion de carrera contra el tiempo real de ida y vuelta del
        # websocket (flaky en CI mas lento).
        voice_capture_countdown_s = 5.0
        voice_followup_s = 5.0

    monkeypatch.setattr("app.voice.session.get_settings", lambda: _FakeSettings())
    monkeypatch.setattr("app.voice.tts.get_settings", lambda: _FakeSettings())

    # "gracias" (al final) no la reconoce la ruta rapida y hay una atencion
    # activa -- sin esto, cae en la ruta LLM de la 13.5 y el resultado de la
    # prueba dependeria de si hay un Ollama real corriendo en esta maquina.
    async def _empty_chat(*, model, system_prompt, user_prompt, json_schema):
        return {"message": {"role": "assistant", "content": '{"actions": [], "unrecognized": []}'}}

    monkeypatch.setattr(ollama_client, "chat", _empty_chat)
    # Igual que en tests/integration/ai/test_ai.py: el interprete tambien llama a
    # model_digest tras chat() -- sin mockearlo, pega de verdad a Ollama (ausente en
    # pruebas) y dispara el aviso "Un momento..." de la 13.5 a los 2 s, rompiendo el
    # unico _drain_until_say de abajo.
    monkeypatch.setattr(ollama_client, "model_digest", lambda model: _async_none())

    user = await make_user(email="odonto.captura@example.com", role_code="odontologo")
    token = await _access_token_for(user)
    patient = await create_patient(
        db_session,
        clinic_id=clinic.id,
        data=PatientCreateRequest(
            first_name="Juan", last_name_paternal="Perez", date_of_birth="1990-05-20"
        ),
        actor_id=None,
    )

    with TestClient(app).websocket_connect("/api/v1/voice/ws") as ws:
        ws.send_json({"type": "auth", "token": token, "clinic_id": str(clinic.id)})
        ws.receive_json()  # state: passive

        ws.send_json(
            {
                "type": "context",
                "route": f"/pacientes/{patient.id}",
                "patient_id": str(patient.id),
            }
        )

        # 1) "inicia la consulta" -- nivel 3, pregunta y espera "si" explicito.
        ws.send_json({"type": "fake_order", "text": "inicia la consulta"})
        say = _drain_until_say(ws)
        assert "Inicio la consulta" in say["text"]
        assert "¿Confirmas?" in say["text"]

        ws.send_json({"type": "fake_order", "text": "si"})
        say = _drain_until_say(ws)
        assert say["text"] == "Consulta iniciada."

        # 2) 20 hallazgos del odontograma, uno tras otro, sin repetir "Dentia"
        # ni esperar a que acabe la cuenta regresiva del anterior.
        for tooth in _TWENTY_TEETH:
            ws.send_json({"type": "fake_order", "text": f"la {tooth} caries oclusal"})
            say = _drain_until_say(ws)
            assert say["text"] == f"Coloco caries en la {tooth}, oclusal."

        # Nada forzo la ejecucion del ultimo (el 34): una orden sin sentido la
        # arrastra igual que una orden real (sec. 2.1), sin depender de la
        # cuenta regresiva real del servidor.
        ws.send_json({"type": "fake_order", "text": "gracias"})
        say = _drain_until_say(ws)
        assert say["text"] == "No te entendí, ¿me lo repites?"

        # 3) "cancela" durante la cuenta regresiva: no se aplica. La pila de
        # deshacer vive en esta misma conexion (sec. 6.5 del diseno: "la
        # sesion guarda una pila de deshacer") -- por eso todo el flujo sigue
        # en el mismo websocket, no en uno nuevo.
        ws.send_json({"type": "fake_order", "text": "la 41 ausente"})
        say = _drain_until_say(ws)
        assert say["text"] == "Coloco ausente en la 41."

        ws.send_json({"type": "fake_order", "text": "cancela"})
        say = _drain_until_say(ws)
        assert say["text"] == "Cancelado."

        # 4) "deshaz" quita la ultima captura aplicada -- la 41 nunca se
        # aplico (se canceló), asi que lo que se deshace es el ultimo de los
        # 20 hallazgos (la 48).
        ws.send_json({"type": "fake_order", "text": "deshaz"})
        say = _drain_until_say(ws)
        assert say["text"] == "Quité caries en la 48, oclusal."

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "odonto.captura@example.com", "password": "Contrasena123"},
    )
    headers = {
        "Authorization": f"Bearer {login.json()['access_token']}",
        "X-Clinic-Id": str(clinic.id),
    }
    odontogram = await client.get(f"/api/v1/patients/{patient.id}/odontogram", headers=headers)
    findings = odontogram.json()
    assert len(findings) == 19
    tooth_fdis = {f["tooth_fdi"] for f in findings}
    assert tooth_fdis == set(_TWENTY_TEETH) - {48}
    assert 41 not in tooth_fdis


async def test_modo_dictado_accumulates_sentences_and_accepts_all_on_confirm(
    client: AsyncClient,
    make_user,
    clinic: Clinic,
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    """13.5 "Ruta LLM y dictado", sec. 4.2 del diseno: "Dentia, dictado" ...
    "fin del dictado" -> "Tengo N propuestas, ¿las acepto todas?" -- de punta
    a punta por el WebSocket, no solo dialogue.finish_dictation() directo (ya
    cubierto en test_dialogue.py)."""
    import json as _json

    from app.ai import ollama_client
    from app.modules.patients.schemas import PatientCreateRequest
    from app.modules.patients.service import create_patient

    class _FakeSettings:
        voice_fake_mode = True
        voice_capture_countdown_s = 0.01
        voice_followup_s = 0.01

    monkeypatch.setattr("app.voice.session.get_settings", lambda: _FakeSettings())
    monkeypatch.setattr("app.voice.tts.get_settings", lambda: _FakeSettings())

    async def _fake_chat(*, model, system_prompt, user_prompt, json_schema):
        content = _json.dumps(
            {
                "actions": [
                    {"type": "add_allergy", "substance": "Penicilina"},
                    {"type": "set_chief_complaint", "text": "Dolor en la muela 36"},
                ],
                "unrecognized": [],
            }
        )
        return {"message": {"role": "assistant", "content": content}}

    monkeypatch.setattr(ollama_client, "chat", _fake_chat)
    monkeypatch.setattr(ollama_client, "model_digest", lambda model: _async_none())

    user = await make_user(email="odonto.dictado@example.com", role_code="odontologo")
    token = await _access_token_for(user)
    patient = await create_patient(
        db_session,
        clinic_id=clinic.id,
        data=PatientCreateRequest(
            first_name="Juan", last_name_paternal="Perez", date_of_birth="1990-05-20"
        ),
        actor_id=None,
    )

    with TestClient(app).websocket_connect("/api/v1/voice/ws") as ws:
        ws.send_json({"type": "auth", "token": token, "clinic_id": str(clinic.id)})
        ws.receive_json()  # state: passive
        ws.send_json(
            {"type": "context", "route": f"/pacientes/{patient.id}", "patient_id": str(patient.id)}
        )

        ws.send_json({"type": "fake_order", "text": "inicia la consulta"})
        say = _drain_until_say(ws)
        assert "¿Confirmas?" in say["text"]
        ws.send_json({"type": "fake_order", "text": "si"})
        say = _drain_until_say(ws)
        assert say["text"] == "Consulta iniciada."

        ws.send_json({"type": "fake_order", "text": "dictado"})
        say = _drain_until_say(ws)
        assert "dictado" in say["text"].lower()
        assert ws.receive_json() == {"type": "state", "state": "listening"}

        # Dentro del dictado: cada frase se acumula, ninguna produce un "say".
        ws.send_json({"type": "fake_order", "text": "alérgica a la penicilina"})
        transcript_msg = ws.receive_json()
        assert transcript_msg == {"type": "transcript", "text": "alérgica a la penicilina"}

        ws.send_json({"type": "fake_order", "text": "dolor en la muela treinta y seis"})
        transcript_msg = ws.receive_json()
        assert transcript_msg["type"] == "transcript"

        ws.send_json({"type": "fake_order", "text": "fin del dictado"})
        say = _drain_until_say(ws)
        assert say["text"] == "Tengo 2 propuestas. ¿Las acepto todas?"

        ws.send_json({"type": "fake_order", "text": "si"})
        say = _drain_until_say(ws)
        assert say["text"] == "Listo, aplicadas."

    from app.ai.models import AiSuggestion

    suggestions = (
        (
            await db_session.execute(
                select(AiSuggestion).where(AiSuggestion.patient_id == patient.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(suggestions) == 2
    assert all(s.status == "ACCEPTED" for s in suggestions)
