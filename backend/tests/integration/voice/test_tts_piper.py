"""Verificacion real de app/voice/tts.py contra el Piper instalado y el modelo
descargado (voices/es_MX-claude-high.onnx) -- a diferencia de la deteccion de
"Dentia" (que necesita un microfono humano real), la sintesis de voz es
determinista y si se puede comprobar de punta a punta sin un navegador. Se
salta sola si el modelo no esta descargado (p.ej. en CI), en vez de fallar."""

from pathlib import Path

import pytest

from app.core.config import get_settings
from app.voice import tts

settings = get_settings()
_MODEL_PATH = Path(settings.voice_tts_model_path) if settings.voice_tts_model_path else None
_MODEL_AVAILABLE = _MODEL_PATH is not None and _MODEL_PATH.is_file()

pytestmark = pytest.mark.skipif(
    not _MODEL_AVAILABLE,
    reason=(
        "voices/es_MX-claude-high.onnx no esta descargado -- "
        "python -m piper.download_voices es_MX-claude-high --download-dir ../voices"
    ),
)


async def test_synthesize_produces_a_playable_wav_and_caches_it() -> None:
    tts._phrase_cache.clear()

    wav = await tts.synthesize("Hola, soy Dentia.")

    assert wav is not None
    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"
    assert len(wav) > 1000  # mas que solo la cabecera: hay audio real
    assert tts._phrase_cache["Hola, soy Dentia."] == wav


async def test_second_call_reuses_the_warm_worker_and_is_much_faster() -> None:
    """Prueba el motivo de piper_worker.py: un proceso nuevo por frase tardaba
    ~3 s (sobre todo cargar el modelo); con el worker caliente, la segunda
    frase (distinta, no toca la cache) deberia resolverse muy por debajo de
    eso. No afirma un numero absoluto (depende de la maquina) -- solo que la
    segunda llamada es claramente mas rapida que arrancar desde cero."""
    import time

    tts._phrase_cache.clear()

    start_cold = time.monotonic()
    first = await tts.synthesize("Primera frase de prueba.")
    elapsed_cold = time.monotonic() - start_cold

    start_warm = time.monotonic()
    second = await tts.synthesize("Segunda frase, distinta de la primera.")
    elapsed_warm = time.monotonic() - start_warm

    assert first is not None
    assert second is not None
    assert elapsed_warm < elapsed_cold
    assert elapsed_warm < 1.5  # presupuesto de la ruta rapida (sec. 5.1 del diseno)
