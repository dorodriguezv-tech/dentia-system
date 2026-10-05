"""Pre-parser deterministico del dictado (docs/03_AGENTE_IA_VOZ.md sec. 2 y 3): convierte
numeros hablados en espanol a FDI y palabras de superficie a su letra. No llama a Ollama ni
a la BD -- son funciones puras sobre texto, para poder probarlas exhaustivamente y para
enviarle "pistas" ya resueltas al modelo en el prompt (ver interpreter.py).
"""

import re
import unicodedata

from app.modules.odontogram.rules import TOOTH_FDI_ALL

_UNITS: dict[str, int] = {
    "cero": 0,
    "uno": 1,
    "un": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
}

_TEENS: dict[str, int] = {
    "diez": 10,
    "once": 11,
    "doce": 12,
    "trece": 13,
    "catorce": 14,
    "quince": 15,
    "dieciseis": 16,
    "diecisiete": 17,
    "dieciocho": 18,
    "diecinueve": 19,
}

_TWENTIES: dict[str, int] = {
    "veinte": 20,
    "veintiuno": 21,
    "veintiun": 21,
    "veintidos": 22,
    "veintitres": 23,
    "veinticuatro": 24,
    "veinticinco": 25,
    "veintiseis": 26,
    "veintisiete": 27,
    "veintiocho": 28,
    "veintinueve": 29,
}

_TENS: dict[str, int] = {
    "treinta": 30,
    "cuarenta": 40,
    "cincuenta": 50,
    "sesenta": 60,
    "setenta": 70,
    "ochenta": 80,
    "noventa": 90,
}

# Palabras que anteceden una pieza dental en el dictado (docs sec. 2): "pieza 36",
# "organo dentario 36", "diente 36". El articulo solo ("la 36", "el 36") tambien cuenta,
# pero no se lista aqui porque se maneja aparte (es ambiguo fuera de contexto dental).
_TOOTH_TRIGGER_WORDS = {"pieza", "diente", "organo", "dentario"}

_SURFACE_WORDS: dict[str, str] = {
    "oclusal": "O",
    "mesial": "M",
    "distal": "D",
    "vestibular": "V",
    "bucal": "V",
    "lingual": "L",
    "palatino": "P",
    "palatina": "P",
    "incisal": "I",
}


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _tokenize(text: str) -> list[str]:
    normalized = _strip_accents(text.lower())
    return re.findall(r"[a-z0-9]+", normalized)


def _number_word_value(word: str) -> int | None:
    if word in _UNITS:
        return _UNITS[word]
    if word in _TEENS:
        return _TEENS[word]
    if word in _TWENTIES:
        return _TWENTIES[word]
    if word in _TENS:
        return _TENS[word]
    if word.isdigit():
        return int(word)
    return None


def _consume_number(tokens: list[str], start: int) -> tuple[int | None, int]:
    """Intenta leer un numero a partir de tokens[start]. Devuelve (valor, tokens_consumidos).

    Soporta: digitos ("36"), palabras compuestas ("treinta y seis" = 30 + 6), palabras
    unicas (teens, veintes, decenas, unidades) y dos unidades seguidas como secuencia de
    digitos hablados ("tres seis" = 36, muy comun al dictar piezas dentales)."""
    if start >= len(tokens):
        return None, 0

    first = tokens[start]

    # "treinta y seis" / "cuarenta y seis": decena + "y" + unidad.
    if first in _TENS and start + 2 < len(tokens) and tokens[start + 1] == "y":
        unit = _UNITS.get(tokens[start + 2])
        if unit is not None:
            return _TENS[first] + unit, 3

    # "tres seis": dos unidades (0-9) seguidas se leen como digitos de una pieza FDI.
    if first in _UNITS and start + 1 < len(tokens):
        second = _UNITS.get(tokens[start + 1])
        if second is not None:
            return _UNITS[first] * 10 + second, 2

    value = _number_word_value(first)
    if value is not None:
        return value, 1

    return None, 0


def extract_tooth_mentions(text: str) -> list[int]:
    """Encuentra menciones de piezas FDI validas (11-48, 51-85) en el texto dictado."""
    tokens = _tokenize(text)
    found: list[int] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        is_trigger = token in _TOOTH_TRIGGER_WORDS
        is_article = token in ("la", "el")
        if is_trigger or is_article:
            value, consumed = _consume_number(tokens, i + 1)
            if value is not None and value in TOOTH_FDI_ALL:
                found.append(value)
                i += 1 + consumed
                continue
        i += 1
    return found


def extract_surfaces(text: str) -> list[str]:
    """Encuentra palabras de superficie (oclusal, mesial, distal...) y las normaliza a
    su letra (O, M, D, V, L, P, I), en el orden en que aparecen, sin duplicados."""
    tokens = _tokenize(text)
    surfaces: list[str] = []
    for token in tokens:
        letter = _SURFACE_WORDS.get(token)
        if letter is not None and letter not in surfaces:
            surfaces.append(letter)
    return surfaces


def normalize_surface_word(word: str) -> str | None:
    return _SURFACE_WORDS.get(_strip_accents(word.lower()))


def build_hints(text: str) -> str:
    """Resumen de piezas y superficies ya resueltas, para incluir como pista en el
    prompt de Ollama (docs sec. 6: "el pre-parser envia al modelo los numeros FDI ya
    resueltos como pistas")."""
    teeth = extract_tooth_mentions(text)
    surfaces = extract_surfaces(text)
    parts = []
    if teeth:
        parts.append(f"piezas detectadas: {', '.join(str(t) for t in teeth)}")
    if surfaces:
        parts.append(f"superficies detectadas: {', '.join(surfaces)}")
    return "; ".join(parts) if parts else "sin pistas detectadas"
