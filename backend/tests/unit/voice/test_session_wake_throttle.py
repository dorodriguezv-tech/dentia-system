"""Bug real encontrado verificando el sistema en vivo (no en docs/06...): con la
escucha pasiva de Dentia abierta, el proceso de uvicorn llegaba a ~400% CPU.
Causa: `VoiceSession._process_wake_audio` volvia a transcribir con Whisper el
bufer completo en CADA frame de audio que llegaba (el AudioWorklet real manda
uno cada ~30 ms, ver frontend/src/modules/voice/audioCapture.ts) una vez que el
bufer pasaba el umbral de 1.5 s -- con voz/ruido de consultorio de por medio,
eso disparaba Whisper decenas de veces por segundo mientras la sesion
estuviera abierta y sin silenciar.
"""

from app.voice import wake
from app.voice.session import VoiceSession


async def test_wake_audio_throttles_whisper_calls_to_avoid_a_cpu_busy_loop(
    monkeypatch,
) -> None:
    class _FakeSettings:
        voice_fake_mode = False

    monkeypatch.setattr("app.voice.session.get_settings", lambda: _FakeSettings())

    call_count = 0

    def _fake_transcribe(audio):  # noqa: ARG001
        nonlocal call_count
        call_count += 1
        return ""

    monkeypatch.setattr(wake, "transcribe_wake_candidate", _fake_transcribe)

    session = VoiceSession(
        websocket=None,  # type: ignore[arg-type]
        db=None,  # type: ignore[arg-type]
        user=None,  # type: ignore[arg-type]
        clinic_id=None,  # type: ignore[arg-type]
    )

    # Frame real: ~30 ms a 16 kHz PCM16 mono (480 muestras * 2 bytes). 150
    # frames (~4.5 s de audio) llegando uno tras otro sin pausas reales entre
    # ellos, igual que mandaria el AudioWorklet si alguien habla cerca del
    # microfono varios segundos seguidos.
    frame = b"\x10\x00" * 480
    for _ in range(150):
        await session._handle_audio_frame(frame)

    # Antes de la correccion esto daba ~100 (una transcripcion por cada frame
    # despues de que el bufer pasara el umbral de 1.5 s, sin ningun limite).
    assert call_count <= 3
