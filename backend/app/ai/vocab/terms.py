"""Fuentes del vocabulario odontologico combinado (Fase 13, C3 del doc 06):
usado tanto para `initial_prompt`/`hotwords` de faster-whisper como para la
correccion post-transcripcion con rapidfuzz (ver `app/ai/vocab/correct.py` y
`app/ai/stt.py`).

Combina DOS fuentes, a proposito (ninguna sola basta):
1. El diccionario externo (`terminos_dentales.txt`, generado por
   `python -m app.ai.vocab.build` -- vacio si todavia no se ha corrido, lo
   que simplemente reduce cobertura, nunca rompe nada).
2. Las ETIQUETAS (no los codigos internos) de los catalogos clinicos FIJOS
   de este sistema (hallazgos del odontograma, diagnosticos). El diccionario
   externo no necesariamente trae estas frases exactas -- por ejemplo
   "pulpitis reversible" (el ejemplo del diseno, sec. 3 del doc 05) es una
   etiqueta de `app/modules/diagnosis/rules.py`, no una entrada del PDF.

Los catalogos ADMINISTRABLES por sucursal (B1: tipos de cita, procedimientos
del catalogo de precios...) viven en la base de datos -- agregarlos exige
contexto de clinica/pantalla en cada transcripcion, que hoy no tienen
`stt.transcribe()`/`transcribe_pcm16()` (funciones puras sobre audio, sin
sesion de BD). Queda pendiente, ver docs/PENDIENTES_CLINICOS.md.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.modules.diagnosis.rules import DIAGNOSIS_CATALOG
from app.modules.odontogram.finding_catalog import FINDING_CATALOG

_TERMS_TXT = Path(__file__).parent / "terminos_dentales.txt"


@lru_cache(maxsize=1)
def dictionary_terms() -> tuple[str, ...]:
    """Vacio si `python -m app.ai.vocab.build` no se ha corrido todavia."""
    if not _TERMS_TXT.exists():
        return ()
    lines = _TERMS_TXT.read_text(encoding="utf-8").splitlines()
    return tuple(line.strip() for line in lines if line.strip())


@lru_cache(maxsize=1)
def catalog_terms() -> tuple[str, ...]:
    labels = [item["label"].lower() for item in FINDING_CATALOG.values()]
    labels += [label.lower() for label in DIAGNOSIS_CATALOG.values()]
    return tuple(sorted(set(labels)))


@lru_cache(maxsize=1)
def combined_vocabulary() -> tuple[str, ...]:
    """Union de las dos fuentes, sin duplicados -- lo que usan `hotwords` y
    la correccion con rapidfuzz (sec 7)."""
    return tuple(sorted(set(catalog_terms()) | set(dictionary_terms())))
