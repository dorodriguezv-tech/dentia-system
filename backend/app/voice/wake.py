"""Deteccion de la palabra de activacion "Dentia" -- etapa 1 del diseno
(docs/05_ASISTENTE_DENTIA_VOZ_CONVERSACIONAL.md sec. 5): VAD (Silero, incluido en
faster-whisper) para descartar silencio rapido, y Whisper "tiny" sobre lo que
tenga voz, verificando que la frase **empiece** por "Dentia". La etapa 2 (modelo
propio openWakeWord/livekit-wakeword) es trabajo de la Fase 13.6 -- no entrenado
aqui, solo deja el interruptor listo (`VOICE_WAKE_ENGINE`).

Carga perezosa de una instancia de WhisperModel separada de la de app/ai/stt.py:
esa usa el modelo configurable (por defecto "small") para transcribir ordenes
completas; esta siempre usa uno pequeno y rapido ("tiny" por defecto) solo para
decidir si alguien dijo "Dentia", sobre fragmentos de ~1-2 s.
"""

import re
import unicodedata

import numpy as np
from faster_whisper import WhisperModel

from app.core.config import get_settings

SAMPLE_RATE = 16_000

# Primera palabra aceptada tras normalizar (sin acentos, minusculas): cubre las
# confusiones foneticas mas probables de Whisper con "Dentia" en espanol. Lista a
# refinar con el corpus de evaluacion de la Fase 13.6 -- un primer intento
# razonable, no la palabra final.
_WAKE_FIRST_WORDS = {"dentia", "dencia", "dentía"}

_wake_model: WhisperModel | None = None


def get_wake_model() -> WhisperModel:
    global _wake_model
    if _wake_model is None:
        settings = get_settings()
        _wake_model = WhisperModel(
            settings.voice_wake_model_size,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    return _wake_model


def pcm16_to_float32(pcm_bytes: bytes) -> np.ndarray:
    """Convierte PCM16 mono little-endian (lo que manda el AudioWorklet del
    navegador) al arreglo float32 en [-1, 1] que espera faster-whisper."""
    if len(pcm_bytes) % 2:
        pcm_bytes = pcm_bytes[:-1]
    ints = np.frombuffer(pcm_bytes, dtype="<i2")
    return (ints.astype(np.float32) / 32768.0).copy()


_SPEECH_RMS_THRESHOLD = 0.01


def rms(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio))))


def has_speech(audio: np.ndarray) -> bool:
    """Filtro barato antes de transcribir: evita correr Whisper sobre silencio
    puro (la mayoria del tiempo, en escucha pasiva). Umbral simple de energia
    en vez de cargar el VAD completo de Silero para un descarte tan basico --
    el VAD real decide donde empieza/termina la frase dentro de
    WhisperModel.transcribe(vad_filter=True). La misma funcion `rms()` la
    reutiliza app/voice/session.py para el fin de orden por silencio (13.2)."""
    return rms(audio) > _SPEECH_RMS_THRESHOLD


def transcribe_wake_candidate(audio: np.ndarray) -> str:
    if not has_speech(audio):
        return ""
    model = get_wake_model()
    segments, _info = model.transcribe(audio, language="es", vad_filter=True, beam_size=1)
    return " ".join(segment.text.strip() for segment in segments).strip()


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9 ]", "", text).strip()


def is_wake_phrase(transcript: str) -> bool:
    """True si la frase empieza por "Dentia" (o una variante fonetica cercana),
    normalizando acentos/mayusculas/puntuacion. No es un match difuso general --
    a proposito, para no despertar con "dentista" (sec. 5 del diseno)."""
    normalized = _normalize(transcript)
    if not normalized:
        return False
    first_word = normalized.split(" ", 1)[0]
    return first_word in _WAKE_FIRST_WORDS
