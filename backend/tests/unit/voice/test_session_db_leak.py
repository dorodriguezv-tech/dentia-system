"""Bug real encontrado verificando el sistema en vivo (no en docs/06...):
`pg_stat_activity` mostraba una conexion "idle in transaction" desde hacia mas
de 2 minutos, ejecutando la consulta de permisos de `user_has_any_permission`
-- la que corre `authenticate()` del WebSocket de voz. Causa: `authenticate()`
hace dos SELECT (auto-begin de SQLAlchemy) y nunca confirma ni revierte esa
transaccion antes de devolver el control a `VoiceSession.run()`, que se queda
esperando el siguiente mensaje (`await websocket.receive()`) sin limite de
tiempo -- "escucha pasiva desde el inicio de sesion" (docs/05...) puede durar
horas. Si el cliente desaparece sin cerrar limpio (pestana cerrada, red caida,
navegacion que no alcanza a correr la limpieza de JS), esa conexion de BD
queda "idle in transaction" para siempre, ocupando un lugar del pool de
conexiones -- con pocas sesiones de voz abandonadas el pool (pequeno por
default) se agota y toda la app empieza a colgarse (visto en vivo: `curl` sin
auth a /patients tardo mas de 10 s sin responder).
"""

import json

from fastapi import WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token
from app.modules.iam.models import Clinic, User
from app.voice.session import handle_connection


class _FakeWebSocket:
    def __init__(self, auth_message: dict) -> None:
        self._auth_message = auth_message
        self._receive_text_called = False

    async def accept(self) -> None:
        return None

    async def receive_text(self) -> str:
        self._receive_text_called = True
        return json.dumps(self._auth_message)

    async def receive(self) -> dict:
        # Simula que el cliente desaparecio justo despues de autenticarse --
        # pestana cerrada, red caida, o una navegacion que no alcanzo a correr
        # la limpieza de JS -- sin un cierre limpio del WebSocket.
        raise WebSocketDisconnect

    async def send_json(self, data: dict) -> None:
        return None

    async def close(self) -> None:
        return None


async def test_authenticate_does_not_leave_the_db_session_in_an_open_transaction(
    make_user,
    clinic: Clinic,
    db_session: AsyncSession,
    monkeypatch,
) -> None:
    # Este test cubre la fuga de transaccion de authenticate(), independiente de si
    # el asistente de IA esta prendido o apagado (AI_ENABLED=false en .env haria que
    # handle_connection() retorne antes de llegar a authenticate(), sin ejercer lo
    # que este test verifica).
    monkeypatch.setattr(get_settings(), "ai_enabled", True)

    user: User = await make_user(email="odonto.leak@example.com", role_code="odontologo")
    token, _jti, _expires_at = create_access_token(user.id)

    ws = _FakeWebSocket({"type": "auth", "token": token, "clinic_id": str(clinic.id)})

    await handle_connection(ws, db_session)  # type: ignore[arg-type]

    # Antes de la correccion esto daba True: las dos consultas de
    # `user_has_any_permission`/`db.get(User, ...)` de `authenticate()` dejaban
    # la transaccion abierta (autobegin de SQLAlchemy) sin que nada la cerrara
    # mientras la sesion de voz esperara el siguiente mensaje.
    assert db_session.in_transaction() is False
