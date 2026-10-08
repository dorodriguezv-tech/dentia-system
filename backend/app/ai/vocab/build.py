"""Extrae el vocabulario odontologico de un diccionario en PDF (Fase 13,
C3 del doc 06 "docs/06_INSTRUCCIONES_CLAUDE_CODE_CORRECCIONES_Y_FASE13.md"):
cada entrada del diccionario ("TERMINO, SINONIMO. Definicion...") se
convierte en una o mas palabras/frases de `terminos_dentales.txt`, con una
categoria opcional (el parentesis que a veces sigue al termino, cuando no es
una remision "Ver X") en `terminos_dentales.json`.

Deliberadamente NO es un analizador de diccionarios perfecto: el objetivo es
una lista de vocabulario para `initial_prompt`/`hotwords` de faster-whisper y
correccion con `rapidfuzz` (app/ai/stt.py), no una base de datos lexica --
un puñado de entradas de mas (una remision, un nombre propio de la
bibliografia) es inofensivo; lo que si importa es no perder terminos reales
ni inventar nada si el PDF resulta ser un escaneo sin texto.

Uso:
    python -m app.ai.vocab.build --source ../docs/Diccionario_odontologico_2023.pdf
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import pdfplumber

_OUT_DIR = Path(__file__).parent
_TERMS_TXT = _OUT_DIR / "terminos_dentales.txt"
_TERMS_JSON = _OUT_DIR / "terminos_dentales.json"

# Encabezado de la seccion de bibliografia, tipografiado con espacios entre
# cada letra ("B I B L I O G R A F I A") -- todo lo que sigue son citas de
# libros/articulos, no entradas del diccionario. Requiere un espacio real
# entre cada letra (no basta "bibliografia" aparecer como palabra suelta en
# el texto normal, p.ej. en la introduccion).
_BIBLIOGRAFIA_RE = re.compile(r"B\s+I\s+B\s+L\s+I\s+O\s+G\s+R\s+A\s+F\s+[IÍ]\s+A")

# Una entrada es "TERMINO[, SINONIMO...]. Definicion" -- el termino (y sus
# sinonimos antes del punto) va siempre en mayusculas. El separador entre
# sinonimos NO incluye el salto de linea a proposito: una letra sola en su
# propio renglon ("A", "B"...) es el divisor alfabetico de seccion, no parte
# del termino siguiente -- permitir aqui el salto de linea los fusionaria en
# un solo encabezado invalido (visto durante el desarrollo de este script).
_HEADER_RE = re.compile(
    r"(?:^|\n)([A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ0-9\-/]*(?:[ ,]+[A-ZÁÉÍÓÚÑÜ][A-ZÁÉÍÓÚÑÜ0-9\-/]*)*)"
    r"\.(?:\s*(\([^)]{1,60}\)))?\s",
    re.MULTILINE,
)

# Umbral para detectar un PDF escaneado (sin texto real, solo imagenes): muy
# pocos caracteres de texto por pagina.
_MIN_CHARS_PER_PAGE = 50


def _is_noise(header: str) -> bool:
    """Encabezados espaciados tipo "B I B L I O G R A F I A" que sobrevivieron
    sueltos (p.ej. si `_BIBLIOGRAFIA_RE` no los alcanzo a cubrir todos) --
    muchas palabras de una sola letra es la senal."""
    words = header.split()
    if not words:
        return True
    one_char_words = sum(1 for w in words if len(w) == 1)
    return len(words) > 3 and one_char_words / len(words) > 0.5


def extract_terms(pdf_path: Path) -> dict[str, str | None]:
    """Devuelve {termino_normalizado: categoria_o_None}. Lanza `ValueError`
    si el PDF no tiene suficiente texto extraible (probablemente escaneado)
    -- el llamador debe avisar, nunca inventar un vocabulario."""
    with pdfplumber.open(pdf_path) as pdf:
        pages_text = [page.extract_text() or "" for page in pdf.pages]

    if not pages_text or (sum(len(t) for t in pages_text) / len(pages_text)) < _MIN_CHARS_PER_PAGE:
        raise ValueError(
            f"'{pdf_path}' no tiene suficiente texto extraible por pagina "
            "(promedio menor a lo esperado) -- probablemente es un PDF escaneado. "
            "No se genero ningun vocabulario; revisa el archivo o conviertelo con OCR."
        )

    full_text = "\n".join(pages_text)
    biblio_match = _BIBLIOGRAFIA_RE.search(full_text)
    if biblio_match:
        full_text = full_text[: biblio_match.start()]

    terms: dict[str, str | None] = {}
    for match in _HEADER_RE.finditer(full_text):
        header = match.group(1)
        if _is_noise(header):
            continue
        category_raw = match.group(2)
        category: str | None = None
        if category_raw:
            inner = category_raw.strip("()").strip()
            if inner and not inner.lower().startswith(("ver ", "vease", "véase")):
                category = inner

        for part in header.split(","):
            part = part.strip().strip("-").strip()
            if len(part) < 2:
                continue
            key = unicodedata.normalize("NFC", part.lower())
            if key not in terms or terms[key] is None:
                terms[key] = category

    if not terms:
        raise ValueError(
            f"No se reconocio ninguna entrada de diccionario en '{pdf_path}' -- "
            "revisa el formato del PDF antes de confiar en este extractor."
        )
    return terms


def write_outputs(terms: dict[str, str | None]) -> None:
    _TERMS_TXT.write_text("\n".join(sorted(terms)) + "\n", encoding="utf-8")
    _TERMS_JSON.write_text(
        json.dumps(terms, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Ruta al PDF del diccionario odontologico",
    )
    args = parser.parse_args(argv)

    try:
        terms = extract_terms(args.source)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    write_outputs(terms)
    with_category = sum(1 for v in terms.values() if v)
    print(f"{len(terms)} terminos escritos en {_TERMS_TXT}")
    print(f"{with_category} con categoria en {_TERMS_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
