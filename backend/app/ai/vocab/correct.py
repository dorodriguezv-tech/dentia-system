"""Correccion de la transcripcion con `rapidfuzz` contra el vocabulario
odontologico combinado (Fase 13, C3 del doc 06, sec. 3 del diseno): palabras
o frases de dos palabras que Whisper transcribio casi-bien ("pulpitis
reversibe") se corrigen contra el termino real del vocabulario SOLO si la
similitud es alta -- a proposito conservador (umbral alto, largo minimo) para
no "corregir" una palabra comun del espanol por un termino tecnico parecido.

Funcion pura sobre texto (sin IO ni BD), igual que `app/ai/dental_parser.py` y
`app/voice/nlu_fast.py` -- para poder probarla exhaustivamente sin mockear
nada."""

from __future__ import annotations

from collections.abc import Sequence

from rapidfuzz import fuzz, process

# Palabras de menos de esto nunca se intentan corregir -- demasiado cortas
# para que una similitud alta signifique algo (p.ej. "sana" casi calza con
# muchas cosas por pura casualidad de longitud).
_MIN_WORD_LENGTH = 5
# Alto a proposito: solo corrige errores de 1-2 caracteres tipicos de una
# transcripcion casi-correcta, no palabras genuinamente distintas.
_SCORE_CUTOFF = 85.0


def correct_transcript(text: str, vocabulary: Sequence[str]) -> str:
    """Revisa pares de palabras consecutivas contra las frases de dos
    palabras del vocabulario (p.ej. "pulpitis reversible") y, si no hay una,
    la palabra sola contra las de una palabra. Las dos bolsas se mantienen
    SEPARADAS a proposito -- un par nunca se corrige contra un termino de
    una sola palabra (de lo contrario "endodoncia en" podria calzar "de
    pura casualidad" contra "endodoncia" sola y tragarse la palabra "en",
    bug real encontrado probando esto con el corpus de 13.6)."""
    if not text or not vocabulary:
        return text

    phrase_lookup = {t.lower(): t for t in vocabulary if " " in t}
    word_lookup = {t.lower(): t for t in vocabulary if " " not in t}
    words = text.split(" ")
    result: list[str] = []
    i = 0
    while i < len(words):
        if i + 1 < len(words):
            bigram = f"{words[i]} {words[i + 1]}"
            corrected = _best_match(bigram, phrase_lookup)
            if corrected is not None:
                result.append(_restore_case(bigram, corrected))
                i += 2
                continue

        corrected = _best_match(words[i], word_lookup)
        if corrected is not None:
            result.append(_restore_case(words[i], corrected))
        else:
            result.append(words[i])
        i += 1

    return " ".join(result)


def _best_match(candidate: str, vocab_lookup: dict[str, str]) -> str | None:
    if not vocab_lookup:
        return None
    stripped = candidate.strip(",.;:¿?¡!")
    if len(stripped) < _MIN_WORD_LENGTH:
        return None
    lowered = stripped.lower()
    if lowered in vocab_lookup:
        return None  # ya es exacto (salvo mayusculas) -- nada que corregir
    match = process.extractOne(
        lowered, vocab_lookup.keys(), scorer=fuzz.ratio, score_cutoff=_SCORE_CUTOFF
    )
    if match is None:
        return None
    matched_key, _score, _index = match
    return vocab_lookup[matched_key]


def _restore_case(original: str, corrected: str) -> str:
    """Si la palabra original empezaba en mayuscula (inicio de frase, nombre
    propio transcrito asi por error...), la correccion tambien -- para no
    imponer minusculas a mitad de una oracion."""
    if original[:1].isupper():
        return corrected[:1].upper() + corrected[1:]
    return corrected
