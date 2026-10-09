"""Pendiente #47 (resto de C3): verifica que `VoiceSession._finalize_order`
(session.py) de verdad pasa el vocabulario por contexto a la transcripcion --
`test_vocab_context.py` ya prueba `vocab_context.contextual_terms()` aislada,
esto prueba el cableado real en session.py (y que el rollback nuevo no deja
la transaccion abierta ni rompe el resto del flujo)."""

from app.ai import stt
from app.modules.iam.models import User
from app.voice.session import VoiceSession


class _FakeWebSocket:
    async def send_json(self, data: dict) -> None:
        return None


async def test_finalize_order_passes_contextual_terms_to_transcription(
    monkeypatch, make_user, clinic, db_session
) -> None:
    user: User = await make_user(email="odonto.vocab.wiring@example.com", role_code="odontologo")
    session = VoiceSession(
        websocket=_FakeWebSocket(),  # type: ignore[arg-type]
        db=db_session,
        user=user,
        clinic_id=clinic.id,
        has_clinical=True,
    )

    captured: dict[str, object] = {}

    def fake_transcribe_pcm16(audio, *, extra_hotwords=()):  # noqa: ANN001, ARG001
        captured["extra_hotwords"] = extra_hotwords
        return "dentia ayuda"

    monkeypatch.setattr(stt, "transcribe_pcm16", fake_transcribe_pcm16)

    run_order_calls: list[str] = []

    async def fake_run_order(text: str) -> None:
        run_order_calls.append(text)

    monkeypatch.setattr(session, "_run_order", fake_run_order)

    session._order_buffer = bytearray(b"\x10\x00" * 2000)
    await session._finalize_order()

    assert run_order_calls == ["dentia ayuda"]
    # Etiqueta sembrada del catalogo de la sucursal (ver tests/conftest.py) --
    # confirma que vino de verdad de vocab_context.contextual_terms(), no de
    # una lista vacia.
    assert "consulta / valoracion" in captured["extra_hotwords"]
    # Mismo cuidado que el bug real de authenticate(): sin el rollback nuevo
    # en _finalize_order, esto quedaria en True (transaccion abierta de las
    # lecturas de contextual_terms, sin ninguna escritura que la cerrara).
    assert db_session.in_transaction() is False
