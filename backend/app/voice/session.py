"""Manejador de una conexion del WebSocket de voz.

13.1 "Base de voz": autenticar, escuchar en pasivo, detectar "Dentia" (etapa 1,
wake.py) y responder por voz.
13.2 "Navegacion": tras detectar "Dentia", sigue escuchando la orden completa
(fin de frase por silencio -- "endpointing", sec. 6 del diseno) y la resuelve
con el gestor de dialogo (dialogue.py, ruta rapida sin LLM). La orden puede
venir en la MISMA frase que la activacion ("Dentia, abre el expediente de Juan
Perez") o sola, despues de un silencio -- por eso el buffer de la orden se
siembra con lo que ya se habia capturado al detectar la palabra, en vez de
descartarlo.
13.3 "Captura en consulta": `dialogue.handle_order` puede devolver una
captura pendiente (nivel 2 o 3, sec. 3 del diseno) en vez de ejecutar de
inmediato -- esta clase es quien maneja la cuenta regresiva de 3 s ("cancela"
la interrumpe) o la espera de "si"/"no" explicito, y la ventana de
seguimiento de 8 s (sec. 2.1) que deja seguir dando ordenes sin repetir
"Dentia". Ambos son temporizadores de fondo (`asyncio.create_task`): se
cancelan al desconectar o silenciar para no dejar tareas colgadas (mismo tipo
de fuga que tuvo el subproceso de Piper antes de 13.2, ver tts.py).
"""

import asyncio
import base64
import contextlib
import json
import time
import uuid
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import stt
from app.core.config import get_settings
from app.core.deps import user_has_any_permission
from app.core.errors import AppError
from app.core.security import TokenError, decode_token
from app.modules.iam.models import User
from app.voice import dialogue, nlu_fast, tts, wake
from app.voice import service as voice_service
from app.voice.context import ScreenContext

_MAX_UNDO_STACK = 10

# Cuanto audio (en bytes PCM16 mono 16 kHz) se acumula antes de intentar detectar
# "Dentia": ~1.5 s, el presupuesto de "fin de la orden -> respuesta" de la sec. 5.1
# del diseno no aplica aqui (esto es solo la deteccion de la palabra), pero no
# conviene esperar mucho mas sin perder la sensacion de "enciende rapido".
_WAKE_CHUNK_BYTES = int(wake.SAMPLE_RATE * 1.5) * 2
# Tope del bufer circular de escucha pasiva (sec. 9 del diseno: "~2 s que nunca se
# guarda ni se registra" -- aqui ademas nunca se persiste, solo vive en memoria
# mientras la conexion esta abierta).
_MAX_BUFFER_BYTES = int(wake.SAMPLE_RATE * 2.5) * 2

# Captura de la orden (13.2, sec. 2.1 y 6 del diseno): termina al detectar este
# tanto de silencio al final del bufer ("~0.8 s" en el diseno).
_ORDER_SILENCE_S = 0.8
# No se intenta terminar por silencio antes de este minimo -- evita cortar la
# orden si el usuario hace una pausa muy corta justo al empezar a hablar.
_ORDER_MIN_SPEECH_S = 0.3
# Tope de seguridad: una orden no deberia tardar mas que esto en decirse.
_ORDER_MAX_S = 8.0
_ORDER_SILENCE_BYTES = int(wake.SAMPLE_RATE * _ORDER_SILENCE_S) * 2
_ORDER_MIN_BYTES = int(wake.SAMPLE_RATE * _ORDER_MIN_SPEECH_S) * 2
_ORDER_MAX_BYTES = int(wake.SAMPLE_RATE * _ORDER_MAX_S) * 2

VOICE_PERMISSION_CODES = ("voice.use", "voice.clinical")


class VoiceAuthError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message


@dataclass
class VoiceSession:
    websocket: WebSocket
    db: AsyncSession
    user: User
    clinic_id: uuid.UUID
    has_clinical: bool = False
    mode: str = "wake"  # "wake" | "order" | "follow_up" | "dictating" | "muted"
    context: ScreenContext = field(default_factory=ScreenContext)
    last_say: str | None = None
    # 13.3 "Captura en consulta": la atencion activa para `hallazgo` y demas
    # intenciones de consulta -- la fija `iniciar_consulta`, no el cliente (a
    # diferencia de `context`, que si viene del navegador).
    active_encounter_id: str | None = None
    # 13.4 (resto): ultimo paciente que una intencion de agenda resolvio -- para
    # que "agregala a la lista de espera" (C2 del doc 06) sepa a quien se
    # refiere "la" sin que haga falta repetir el nombre.
    last_patient_ref: tuple[str, str] | None = None
    _buffer: bytearray = field(default_factory=bytearray)
    _order_buffer: bytearray = field(default_factory=bytearray)
    # 13.5 "Ruta LLM y dictado": texto acumulado mientras `mode == "dictating"`
    # (ver `_handle_dictation_utterance`) -- una frase por elemento, unidas con
    # espacio al terminar el dictado.
    _dictation_buffer: list[str] = field(default_factory=list, repr=False)
    _pending: dialogue.PendingCapture | None = field(default=None, repr=False)
    _pending_task: asyncio.Task[None] | None = field(default=None, repr=False)
    _followup_task: asyncio.Task[None] | None = field(default=None, repr=False)
    _undo_stack: list[dialogue.UndoEntry] = field(default_factory=list, repr=False)

    async def send_state(self, state: str) -> None:
        await self.websocket.send_json({"type": "state", "state": state})

    async def send_say(self, text: str) -> None:
        # Si Piper no esta configurado/instalado, synthesize() devuelve None y el
        # cliente cae al respaldo documentado (speechSynthesis del navegador,
        # sec. 5 del diseno) -- nunca se queda muda.
        audio_wav = await tts.synthesize(text)
        audio_base64 = base64.b64encode(audio_wav).decode("ascii") if audio_wav else None
        await self.websocket.send_json({"type": "say", "text": text, "audio": audio_base64})
        self.last_say = text

    async def send_ui_action(self, action: dialogue.UiAction) -> None:
        await self.websocket.send_json(
            {"type": "ui_action", "action": action.action, "payload": action.payload}
        )

    async def send_error(self, code: str, message: str) -> None:
        await self.websocket.send_json({"type": "error", "code": code, "message": message})

    async def run(self) -> None:
        await self.send_state("passive")
        try:
            while True:
                message = await self.websocket.receive()
                if message["type"] == "websocket.disconnect":
                    return
                if message.get("bytes") is not None:
                    await self._handle_audio_frame(message["bytes"])
                elif message.get("text") is not None:
                    await self._handle_text_frame(message["text"])
        except WebSocketDisconnect:
            return
        finally:
            await self._cancel_background_tasks()

    async def _cancel_background_tasks(self) -> None:
        for task in (self._pending_task, self._followup_task):
            if task is not None:
                task.cancel()
        for task in (self._pending_task, self._followup_task):
            if task is not None:
                with contextlib.suppress(asyncio.CancelledError):
                    await task
        self._pending_task = None
        self._followup_task = None

    async def _handle_text_frame(self, text: str) -> None:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return
        msg_type = payload.get("type")

        if msg_type == "ui":
            action = payload.get("action")
            if action == "mute":
                self.mode = "muted"
                self._buffer.clear()
                self._order_buffer.clear()
                self._dictation_buffer.clear()
                self._pending = None
                await self._cancel_background_tasks()
                await self.send_state("muted")
            elif action == "unmute":
                self.mode = "wake"
                await self.send_state("passive")
        elif msg_type == "context":
            self.context = ScreenContext.from_message(payload)
        elif msg_type == "fake_wake":
            # Solo con VOICE_FAKE_MODE=true: simula detectar "Dentia" sola, sin
            # ninguna orden despues (equivalente a decir "Dentia" y quedarse
            # callado) -- atajo deterministico para pruebas automatizadas.
            if get_settings().voice_fake_mode:
                await self._on_wake_detected(transcript="dentia (fake)", latency_ms=0)
                await self._run_order("")
        elif msg_type == "fake_order":
            # Igual que "fake_wake", pero simulando que la orden capturada
            # despues de "Dentia" fue el texto dado -- para probar el gestor
            # de dialogo (dialogue.py) sin audio real.
            if get_settings().voice_fake_mode:
                text_order = str(payload.get("text", ""))
                if self.mode == "dictating":
                    # Ya en modo dictado: esta frase se acumula como texto,
                    # no se trata como una orden nueva (ver _run_order sobre
                    # como se entra a este modo).
                    await self._handle_dictation_utterance(text_order)
                else:
                    await self._on_wake_detected(
                        transcript=f"dentia {text_order}".strip(), latency_ms=0
                    )
                    await self._run_order(text_order)

    async def _handle_audio_frame(self, data: bytes) -> None:
        if self.mode == "muted":
            return
        if get_settings().voice_fake_mode:
            # En modo fake no se procesa audio real -- las pruebas usan los
            # mensajes "fake_wake"/"fake_order" en su lugar.
            return

        if self.mode == "wake":
            await self._process_wake_audio(data)
        elif self.mode == "follow_up":
            # Sec. 2.1 del diseno: dentro de la ventana de seguimiento no hace
            # falta repetir "Dentia" -- la primera voz que llega ya es el
            # principio de una orden nueva.
            if self._followup_task is not None:
                self._followup_task.cancel()
                self._followup_task = None
            self.mode = "order"
            await self._process_order_audio(data)
        elif self.mode in ("order", "dictating"):
            await self._process_order_audio(data)

    async def _process_wake_audio(self, data: bytes) -> None:
        self._buffer.extend(data)
        if len(self._buffer) > _MAX_BUFFER_BYTES:
            del self._buffer[: len(self._buffer) - _MAX_BUFFER_BYTES]
        if len(self._buffer) < _WAKE_CHUNK_BYTES:
            return

        started_at = time.monotonic()
        audio = wake.pcm16_to_float32(bytes(self._buffer))
        transcript = wake.transcribe_wake_candidate(audio)
        if wake.is_wake_phrase(transcript):
            latency_ms = int((time.monotonic() - started_at) * 1000)
            # La orden puede venir en la misma frase ("Dentia, abre..."): se
            # siembra el bufer de la orden con lo ya capturado, no se descarta.
            self._order_buffer = bytearray(self._buffer)
            self._buffer = bytearray()
            self.mode = "order"
            await self._on_wake_detected(transcript=transcript, latency_ms=latency_ms)
            await self._maybe_finalize_order()

    async def _process_order_audio(self, data: bytes) -> None:
        self._order_buffer.extend(data)
        await self._maybe_finalize_order()

    async def _maybe_finalize_order(self) -> None:
        buffer_len = len(self._order_buffer)
        if buffer_len >= _ORDER_MAX_BYTES:
            await self._finalize_order()
            return
        if buffer_len < _ORDER_MIN_BYTES:
            return

        trailing = self._order_buffer[-_ORDER_SILENCE_BYTES:]
        if len(trailing) < _ORDER_SILENCE_BYTES:
            return
        audio = wake.pcm16_to_float32(bytes(trailing))
        if not wake.has_speech(audio):
            await self._finalize_order()

    async def _finalize_order(self) -> None:
        was_dictating = self.mode == "dictating"
        self.mode = "wake"
        audio_bytes = bytes(self._order_buffer)
        self._order_buffer = bytearray()
        self._buffer = bytearray()

        audio = wake.pcm16_to_float32(audio_bytes)
        transcript = stt.transcribe_pcm16(audio) if audio.size else ""
        if was_dictating:
            await self._handle_dictation_utterance(transcript)
        else:
            await self._run_order(transcript)

    async def _on_wake_detected(self, *, transcript: str, latency_ms: int) -> None:
        await self.send_state("awake")
        await voice_service.log_command(
            self.db,
            clinic_id=self.clinic_id,
            user_id=self.user.id,
            event="wake_detected",
            transcript=transcript,
            latency_ms=latency_ms,
        )

    async def _run_order(self, text: str) -> None:
        if self._pending is not None:
            await self._handle_pending_reply(text)
            return

        if not nlu_fast.strip_wake_word(text):
            # Transcripcion vacia o solo "Dentia": el usuario no dijo nada mas
            # todavia -- se le invita a seguir, no es un "no te entendi".
            await self.send_state("speaking")
            await self.send_say("¿Sí?")
            await self._enter_follow_up()
            return

        await self.send_state("thinking")
        result = await self._handle_order_with_stall_notice(text)
        if result.pop_undo and self._undo_stack:
            self._undo_stack.pop()
        if result.encounter_id:
            self.active_encounter_id = result.encounter_id
        if result.patient_ref:
            self.last_patient_ref = result.patient_ref

        log_text = result.say or (result.pending.say_preview if result.pending else "")
        await voice_service.log_command(
            self.db,
            clinic_id=self.clinic_id,
            user_id=self.user.id,
            event="order",
            transcript=text,
            result=log_text[:200],
        )

        muted = False
        for action in result.ui_actions:
            await self.send_ui_action(action)
            if action.action == "mute":
                muted = True

        if result.pending is not None:
            await self._start_pending(result.pending)
            return

        if muted:
            self.mode = "muted"
            await self._cancel_background_tasks()
            await self.send_state("speaking")
            await self.send_say(result.say)
            await self.send_state("muted")
            return

        await self.send_state("speaking")
        await self.send_say(result.say)
        if result.start_dictation:
            self.mode = "dictating"
            await self.send_state("listening")
            return
        await self._enter_follow_up()

    async def _handle_order_with_stall_notice(self, text: str) -> dialogue.DialogueResult:
        """Sec. 5.1 y C4 del diseno: si resolver la orden tarda (ruta LLM,
        13.5), avisa "Un momento..." en vez de dejar el silencio -- generico
        para cualquier orden, no solo las que de verdad llegan a Ollama,
        porque `dialogue.py` no conoce el websocket para avisar por su cuenta."""
        task = asyncio.ensure_future(
            dialogue.handle_order(
                self.db,
                clinic_id=self.clinic_id,
                user_id=self.user.id,
                transcript=text,
                context=self.context,
                last_say=self.last_say,
                has_clinical=self.has_clinical,
                active_encounter_id=self.active_encounter_id,
                undo_top=self._undo_stack[-1] if self._undo_stack else None,
                last_patient=self.last_patient_ref,
            )
        )
        done, _pending = await asyncio.wait({task}, timeout=2.0)
        if task not in done:
            await self.send_say("Un momento...")
            await task
        return task.result()

    async def _handle_dictation_utterance(self, text: str) -> None:
        """Una frase mas dentro de "Dentia, dictado" (13.5, sec. 4.2 del
        diseno): se acumula tal cual (sin pasar por `nlu_fast.match`, para no
        perder acentos/puntuacion que le sirven al interprete de la Fase 8) y
        se manda un "transcript" para que la pantalla muestre el avance en
        vivo (sec. 6.1 del diseno) -- solo "fin del dictado" (revisado
        aparte) de verdad "significa algo" en este modo."""
        normalized = nlu_fast.strip_wake_word(text)
        if not normalized:
            self.mode = "dictating"
            return
        if nlu_fast.is_dictation_end(normalized):
            await self._end_dictation()
            return
        self._dictation_buffer.append(text.strip())
        await self.websocket.send_json({"type": "transcript", "text": text.strip()})
        self.mode = "dictating"

    async def _end_dictation(self) -> None:
        transcript = " ".join(self._dictation_buffer)
        self._dictation_buffer = []
        await self.send_state("thinking")
        result = await dialogue.finish_dictation(
            self.db,
            clinic_id=self.clinic_id,
            user_id=self.user.id,
            encounter_id=self.active_encounter_id or "",
            transcript=transcript,
        )
        log_text = result.say or (result.pending.say_preview if result.pending else "")
        await voice_service.log_command(
            self.db,
            clinic_id=self.clinic_id,
            user_id=self.user.id,
            event="dictation",
            transcript=transcript[:500],
            result=log_text[:200],
        )
        if result.pending is not None:
            await self._start_pending(result.pending)
            return
        await self.send_state("speaking")
        await self.send_say(result.say)
        await self._enter_follow_up()

    async def _handle_pending_reply(self, text: str) -> None:
        """La sesion esta esperando "cancela" (cuenta regresiva, nivel 2) o
        "si"/"no" explicito (nivel 3) -- sec. 3 del diseno. Se revisa ANTES
        que el flujo normal de `dialogue.handle_order` mientras `_pending`
        este activo (ver `_run_order`)."""
        pending = self._pending
        assert pending is not None
        confirmation = nlu_fast.match_confirmation(text)

        if pending.level == 2:
            if confirmation == "cancel":
                await self._cancel_pending(pending)
                return
            # Cualquier otra cosa durante la cuenta regresiva significa que el
            # odontologo ya sigue con la siguiente orden: se ejecuta de
            # inmediato (no hace falta esperar el resto de los 3 s) y la orden
            # nueva se procesa a continuacion -- evita perder hallazgos
            # dictados rapido, uno tras otro, sin pausas.
            if self._pending_task is not None:
                self._pending_task.cancel()
                self._pending_task = None
            self._pending = None
            await self._execute_pending(pending)
            await self._run_order(text)
            return

        if confirmation == "confirm":
            self._pending = None
            await self._execute_pending(pending)
        elif confirmation == "cancel":
            await self._cancel_pending(pending)
        else:
            # `_pending` sigue activo (no se limpio arriba): la proxima orden
            # vuelve a pasar por aqui. `self.mode` ya quedo en "wake" (lo puso
            # `_finalize_order` antes de llamar `_run_order`) -- hay que
            # devolverlo a "order" para seguir escuchando sin pedir "Dentia".
            self.mode = "order"
            await self.send_state("speaking")
            await self.send_say("¿Sí o no?")
            await self.send_state("confirming")

    async def _cancel_pending(self, pending: dialogue.PendingCapture) -> None:
        if self._pending_task is not None:
            self._pending_task.cancel()
            self._pending_task = None
        self._pending = None
        await self.send_state("speaking")
        await self.send_say(pending.cancel_say)
        await self._enter_follow_up()

    async def _start_pending(self, pending: dialogue.PendingCapture) -> None:
        self._pending = pending
        say = pending.say_preview
        if pending.confirm_prompt:
            say = f"{say} {pending.confirm_prompt}"
        self.mode = "order"  # sigue escuchando la respuesta sin pedir "Dentia"
        await self.send_state("confirming" if pending.level == 3 else "speaking")
        await self.send_say(say)
        if pending.level == 2:
            await self.send_state("listening")
            self._pending_task = asyncio.create_task(
                self._run_countdown(get_settings().voice_capture_countdown_s)
            )

    async def _run_countdown(self, seconds: float) -> None:
        try:
            await asyncio.sleep(seconds)
        except asyncio.CancelledError:
            return
        pending = self._pending
        self._pending = None
        self._pending_task = None
        # Cualquier murmullo ambiental que no haya llegado a formar una orden
        # completa (p.ej. no alcanzo el minimo de voz) no debe colarse en la
        # siguiente captura.
        self._order_buffer = bytearray()
        if pending is not None:
            await self._execute_pending(pending)

    async def _execute_pending(self, pending: dialogue.PendingCapture) -> None:
        await self.send_state("thinking")
        try:
            result = await pending.execute()
        except AppError as exc:
            # Red de seguridad: cada `execute()` de dialogue.py ya deberia
            # atrapar sus propios AppError esperados (p.ej. traslape de citas,
            # 13.4) y devolver un DialogueResult en vez de dejarlo propagar --
            # esto evita que una intencion nueva que se olvide de hacerlo
            # tumbe la sesion completa de voz.
            result = dialogue.DialogueResult(say=f"No se pudo aplicar: {exc.message}")
        if result.encounter_id:
            self.active_encounter_id = result.encounter_id
        if result.patient_ref:
            self.last_patient_ref = result.patient_ref
        if result.undo_entry is not None:
            self._undo_stack.append(result.undo_entry)
            del self._undo_stack[:-_MAX_UNDO_STACK]
        for action in result.ui_actions:
            await self.send_ui_action(action)
        if result.say:
            await self.send_state("speaking")
            await self.send_say(result.say)
        await self._enter_follow_up()

    async def _enter_follow_up(self) -> None:
        # Sec. 2.1 del diseno: 8 s (configurable) en los que se puede seguir
        # dando ordenes sin repetir "Dentia" -- ver `_handle_audio_frame`.
        if self._followup_task is not None:
            self._followup_task.cancel()
        self.mode = "follow_up"
        await self.send_state("listening")
        self._followup_task = asyncio.create_task(self._followup_timeout())

    async def _followup_timeout(self) -> None:
        try:
            await asyncio.sleep(get_settings().voice_followup_s)
        except asyncio.CancelledError:
            return
        self._followup_task = None
        if self.mode == "follow_up":
            self.mode = "wake"
            await self.send_state("passive")


async def authenticate(websocket: WebSocket, db: AsyncSession) -> tuple[User, uuid.UUID, bool]:
    """Primer mensaje obligatorio: {"type": "auth", "token": ..., "clinic_id": ...}.
    Mismo JWT y X-Clinic-Id que el resto de la API (sec. 9 del diseno) -- Dentia
    nunca puede hacer nada que el usuario no pueda hacer a mano. Devuelve
    tambien si el usuario tiene `voice.clinical` (para gating por intencion,
    ver dialogue.py)."""
    raw = await websocket.receive_text()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise VoiceAuthError("INVALID_AUTH", "Mensaje de autenticacion invalido") from exc

    if payload.get("type") != "auth":
        raise VoiceAuthError("INVALID_AUTH", "El primer mensaje debe ser de tipo 'auth'")

    token = payload.get("token")
    clinic_id_raw = payload.get("clinic_id")
    if not token or not clinic_id_raw:
        raise VoiceAuthError("INVALID_AUTH", "Faltan 'token' o 'clinic_id'")

    try:
        clinic_id = uuid.UUID(str(clinic_id_raw))
    except ValueError as exc:
        raise VoiceAuthError("INVALID_AUTH", "clinic_id invalido") from exc

    try:
        token_payload = decode_token(token, expected_type="access")
    except TokenError as exc:
        raise VoiceAuthError("UNAUTHENTICATED", str(exc)) from exc

    user = await db.get(User, uuid.UUID(token_payload["sub"]))
    if user is None or not user.is_active:
        raise VoiceAuthError("UNAUTHENTICATED", "Usuario invalido o inactivo")

    allowed = await user_has_any_permission(
        db, user_id=user.id, clinic_id=clinic_id, codes=VOICE_PERMISSION_CODES
    )
    if not allowed:
        raise VoiceAuthError("FORBIDDEN", "No tienes permiso para usar el asistente de voz")

    has_clinical = await user_has_any_permission(
        db, user_id=user.id, clinic_id=clinic_id, codes=("voice.clinical",)
    )

    return user, clinic_id, has_clinical


async def handle_connection(websocket: WebSocket, db: AsyncSession) -> None:
    await websocket.accept()
    try:
        user, clinic_id, has_clinical = await authenticate(websocket, db)
    except VoiceAuthError as exc:
        await websocket.send_json({"type": "error", "code": exc.code, "message": exc.message})
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
        return
    except WebSocketDisconnect:
        return

    session = VoiceSession(
        websocket=websocket,
        db=db,
        user=user,
        clinic_id=clinic_id,
        has_clinical=has_clinical,
    )
    await session.run()
