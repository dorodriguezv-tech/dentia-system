"""Transcripcion de voz a texto con faster-whisper (docs/03_AGENTE_IA_VOZ.md sec. 3 y 7).

Carga perezosa de una sola instancia de WhisperModel (modelo configurable via
WHISPER_MODEL/WHISPER_DEVICE/WHISPER_COMPUTE_TYPE en .env): cargarlo tarda varios
segundos, asi que se hace una sola vez por proceso, no en cada peticion.
"""

import io

from faster_whisper import WhisperModel

from app.core.config import get_settings

# Vocabulario dental para initial_prompt (docs sec. 3): ayuda a whisper a reconocer
# terminos clinicos poco comunes en espanol general.
DENTAL_VOCABULARY = (
    "oclusal, mesial, distal, vestibular, bucal, lingual, palatino, incisal, "
    "caries, resina, amalgama, endodoncia, corona, pulpitis, periodontitis, "
    "gingivitis, absceso periapical, necrosis pulpar, edentulismo, maloclusion, "
    "ortodoncia, protesis, implante, sellador, extraccion, organo dentario, FDI."
)

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
    )
    return " ".join(segment.text.strip() for segment in segments).strip()
