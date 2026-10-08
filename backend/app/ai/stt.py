"""Transcripcion de voz a texto con faster-whisper (docs/03_AGENTE_IA_VOZ.md sec. 3 y 7).

Carga perezosa de una sola instancia de WhisperModel (modelo configurable via
WHISPER_MODEL/WHISPER_DEVICE/WHISPER_COMPUTE_TYPE en .env): cargarlo tarda varios
segundos, asi que se hace una sola vez por proceso, no en cada peticion.
"""

import io

import numpy as np
from faster_whisper import WhisperModel

from app.ai.vocab import correct as vocab_correct
from app.ai.vocab import terms as vocab_terms
from app.core.config import get_settings

# Vocabulario dental para initial_prompt (docs sec. 3): ayuda a whisper a reconocer
# terminos clinicos poco comunes en espanol general. Deliberadamente corto (el limite
# de initial_prompt es de ~224 tokens, sec. 3 del doc 05) -- el vocabulario completo
# (diccionario externo + catalogos clinicos, C3 del doc 06) va por `hotwords` en vez,
# que no tiene ese limite, y por `vocab_correct.correct_transcript` despues.
DENTAL_VOCABULARY = (
    "oclusal, mesial, distal, vestibular, bucal, lingual, palatino, incisal, "
    "caries, resina, amalgama, endodoncia, corona, pulpitis, periodontitis, "
    "gingivitis, absceso periapical, necrosis pulpar, edentulismo, maloclusion, "
    "ortodoncia, protesis, implante, sellador, extraccion, organo dentario, FDI."
)


def _hotwords() -> str:
    return " ".join(vocab_terms.combined_vocabulary())


def _correct(text: str) -> str:
    return vocab_correct.correct_transcript(text, vocab_terms.combined_vocabulary())


_model: WhisperModel | None = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        settings = get_settings()
        _model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    return _model


def transcribe(audio_bytes: bytes) -> str:
    """Transcribe un fragmento de audio (webm/opus u otro formato que ffmpeg/PyAV pueda
    decodificar) a texto en espanol. VAD activado para recortar silencios."""
    model = get_model()
    segments, _info = model.transcribe(
        io.BytesIO(audio_bytes),
        language="es",
        vad_filter=True,
        initial_prompt=DENTAL_VOCABULARY,
        hotwords=_hotwords(),
    )
    text = " ".join(segment.text.strip() for segment in segments).strip()
    return _correct(text)


def transcribe_pcm16(audio: np.ndarray) -> str:
    """Igual que `transcribe()`, pero para PCM16 mono crudo ya convertido a
    float32 en [-1, 1] (ver app/voice/wake.py::pcm16_to_float32) -- lo usa
    Dentia (Fase 13) para transcribir la orden completa tras detectar la
    palabra de activacion, sin pasar por un contenedor de audio comprimido."""
    model = get_model()
    segments, _info = model.transcribe(
        audio,
        language="es",
        vad_filter=True,
        initial_prompt=DENTAL_VOCABULARY,
        hotwords=_hotwords(),
    )
    text = " ".join(segment.text.strip() for segment in segments).strip()
    return _correct(text)
