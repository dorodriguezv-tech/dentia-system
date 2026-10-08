"""Texto -> voz para Dentia (13.1 en adelante).

Piper se invoca SIEMPRE como subproceso aparte (`app/voice/piper_worker.py`),
nunca `import piper` en el proceso del backend: el motor activo
(`OHF-Voice/piper1-gpl`, lo que instala `piper-tts` desde oct. 2025) es
GPL-3.0 -- el repo MIT original (`rhasspy/piper`) quedo archivado sin
mantenimiento. Este sistema se distribuye instalado en la PC/servidor de cada
clinica (no se opera como SaaS propio), asi que invocar Piper como proceso
aparte (igual que ya hacemos con Ollama) evita incorporar esa licencia
directamente al programa que lo llama -- mismo razonamiento que usar `ffmpeg`
por subproceso en vez de enlazarlo. No es garantia legal absoluta; ver
docs/PENDIENTES_CLINICOS.md #37.

El subproceso se queda vivo entre llamadas (ver piper_worker.py): levantarlo
por frase tardaba ~3 s (sobre todo cargar el modelo), muy por encima del
presupuesto de latencia de Dentia. Una vez arriba, cada frase nueva tarda del
orden de decimas de segundo.

Si el modelo no esta descargado (`VOICE_TTS_MODEL_PATH` vacio o inexistente) o
`VOICE_TTS_ENGINE` no es "piper", `synthesize()` devuelve None: el cliente ya
sabe caer a `speechSynthesis` del navegador (ttsPlayer.ts) -- Dentia nunca se
queda muda.
"""

import asyncio
import json
import struct
import sys
from pathlib import Path

from app.core.config import get_settings

_WORKER_STARTUP_TIMEOUT_S = 30
_SYNTHESIS_TIMEOUT_S = 10
_MAX_CACHE_ENTRIES = 50

_WORKER_SCRIPT = Path(__file__).with_name("piper_worker.py")

# Fase (sec. 5 del diseno): "Respuestas habladas: frases precalculadas en cache".
_phrase_cache: dict[str, bytes] = {}

_worker_process: asyncio.subprocess.Process | None = None
_worker_config_path: Path | None = None
_worker_lock = asyncio.Lock()


def _model_paths() -> tuple[Path, Path] | None:
    settings = get_settings()
    if settings.voice_tts_engine != "piper" or not settings.voice_tts_model_path:
        return None
    model_path = Path(settings.voice_tts_model_path)
    config_path = model_path.with_name(model_path.name + ".json")
    if not model_path.is_file() or not config_path.is_file():
        return None
    return model_path, config_path


def _sample_rate(config_path: Path) -> int:
    with config_path.open(encoding="utf-8") as f:
        data = json.load(f)
    return int(data.get("audio", {}).get("sample_rate", 22050))


def _pcm_to_wav(pcm: bytes, sample_rate: int) -> bytes:
    """Envuelve el PCM16 mono crudo del worker en un WAV -- mas simple que
    pasar por el modulo `wave` de la stdlib (pide un archivo/buffer con seek)
    para una cabecera de 44 bytes."""
    channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    header = b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt "
    header += struct.pack(
        "<IHHIIHH", 16, 1, channels, sample_rate, byte_rate, block_align, bits_per_sample
    )
    header += b"data" + struct.pack("<I", len(pcm))
    return header + pcm


async def _reset_worker() -> None:
    global _worker_process
    process = _worker_process
    _worker_process = None
    if process is not None and process.returncode is None:
        process.kill()
        await process.wait()


async def shutdown() -> None:
    """Se llama al apagar el backend (ver app/main.py) para no dejar el
    subproceso de Piper huerfano."""
    async with _worker_lock:
        await _reset_worker()


async def _get_worker(model_path: Path, config_path: Path) -> asyncio.subprocess.Process | None:
    global _worker_process, _worker_config_path
    if (
        _worker_process is not None
        and _worker_process.returncode is None
        and _worker_config_path == config_path
    ):
        return _worker_process

    await _reset_worker()

    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(_WORKER_SCRIPT),
        str(model_path),
        str(config_path),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    assert process.stdout is not None
    try:
        ready_line = await asyncio.wait_for(
            process.stdout.readline(), timeout=_WORKER_STARTUP_TIMEOUT_S
        )
    except TimeoutError:
        process.kill()
        return None
    if ready_line.strip() != b"READY":
        process.kill()
        return None

    _worker_process = process
    _worker_config_path = config_path
    return process


async def _read_frame(stdout: asyncio.StreamReader) -> bytes:
    """Lee un frame binario del worker: 4 bytes big-endian de longitud, luego
    exactamente esa cantidad de bytes. Nunca `readline()` para la respuesta --
    unos pocos segundos de PCM superan su limite de linea por defecto."""
    header = await stdout.readexactly(4)
    (length,) = struct.unpack(">I", header)
    if length == 0:
        return b""
    return await stdout.readexactly(length)


async def synthesize(text: str) -> bytes | None:
    """WAV (bytes) de `text`, o None si Piper no esta configurado/instalado."""
    settings = get_settings()
    if settings.voice_fake_mode:
        return None

    if text in _phrase_cache:
        return _phrase_cache[text]

    paths = _model_paths()
    if paths is None:
        return None
    model_path, config_path = paths

    async with _worker_lock:
        process = await _get_worker(model_path, config_path)
        if process is None or process.stdin is None or process.stdout is None:
            return None
        try:
            line_text = text.replace("\n", " ").replace("\r", " ")
            process.stdin.write((line_text + "\n").encode("utf-8"))
            await process.stdin.drain()
            pcm = await asyncio.wait_for(_read_frame(process.stdout), timeout=_SYNTHESIS_TIMEOUT_S)
        except (OSError, TimeoutError, ConnectionError, asyncio.IncompleteReadError):
            await _reset_worker()
            return None

    if not pcm:
        return None

    wav = _pcm_to_wav(pcm, _sample_rate(config_path))
    if len(_phrase_cache) < _MAX_CACHE_ENTRIES:
        _phrase_cache[text] = wav
    return wav
