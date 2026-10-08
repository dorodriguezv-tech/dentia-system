"""Fecha/hora relativas dichas en voz (Fase 13, 13.4 "Diagnostico, plan y
agenda" -- C2 del doc 06, agenda por voz de recepcion): "hoy", "mañana", un
día de la semana, "en N días" para la fecha; "a las 10", "a las 10:30" para
la hora. Funciones puras sobre texto, sin BD, mismo criterio que
app/ai/dental_parser.py y app/voice/nlu_fast.py -- para poder probarlas
exhaustivamente.

Deliberadamente no cubre fechas explícitas ("el 21 de octubre") ni
desambiguación mañana/tarde de la hora (sec. 5 del diseño: la ruta rápida
cubre lo más frecuente; una frase libre cae en "no te entendí" por ahora y
queda para la ruta LLM de la 13.5 -- ver docs/PENDIENTES_CLINICOS.md).
"""

import re
import unicodedata
from datetime import date, time, timedelta

_WEEKDAYS: dict[str, int] = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "domingo": 6,
}

_HOUR_WORDS: dict[str, int] = {
    "una": 1,
    "uno": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
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
    "veinte": 20,
    "veintiuna": 21,
    "veintiuno": 21,
    "veintidos": 22,
    "veintitres": 23,
}


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower().strip())
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^a-z0-9: ]", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def extract_relative_date(text: str, *, today: date) -> date | None:
    """ "hoy"/"mañana" devuelven ese día; un día de la semana devuelve su
    próxima ocurrencia (si hoy mismo es ese día, es hoy); "en N días" suma N
    días. Si no reconoce nada, devuelve None (no adivina una fecha)."""
    norm = _normalize(text)
    if not norm:
        return None

    words = norm.split()
    if "hoy" in words:
        return today
    if "manana" in words:
        return today + timedelta(days=1)

    match_in_days = re.search(r"\ben\s+(\d+)\s+dias?\b", norm)
    if match_in_days:
        return today + timedelta(days=int(match_in_days.group(1)))

    for word, weekday in _WEEKDAYS.items():
        if word in words:
            delta = (weekday - today.weekday()) % 7
            return today + timedelta(days=delta)

    return None


def extract_time_of_day(text: str) -> time | None:
    """ "a las 10", "a las 10:30", "a las diez", "a las diez y media". No
    distingue a.m./p.m. -- la hora se toma tal como se dice (ver limitación
    en docs/PENDIENTES_CLINICOS.md)."""
    norm = _normalize(text)
    if not norm:
        return None

    match_numeric = re.search(r"\ba las\s+(\d{1,2})(?::(\d{2})|\s+(\d{2}))?\b", norm)
    if match_numeric:
        hour = int(match_numeric.group(1))
        minute_raw = match_numeric.group(2) or match_numeric.group(3)
        minute = int(minute_raw) if minute_raw else 0
        return _safe_time(hour, minute)

    match_spoken = re.search(r"\ba las\s+([a-z]+)(\s+y\s+media)?\b", norm)
    if match_spoken:
        spoken_hour = _HOUR_WORDS.get(match_spoken.group(1))
        if spoken_hour is not None:
            minute = 30 if match_spoken.group(2) else 0
            return _safe_time(spoken_hour, minute)

    return None


def _safe_time(hour: int, minute: int) -> time | None:
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return time(hour=hour, minute=minute)


_WEEKDAY_NAMES = (
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
)
_MONTH_NAMES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def format_date_es(value: date) -> str:
    """Para que Dentia diga la fecha en vez de un ISO ("jueves 5 de marzo",
    no "2026-03-05") -- usado al confirmar agendar/reprogramar una cita."""
    return f"{_WEEKDAY_NAMES[value.weekday()]} {value.day} de {_MONTH_NAMES[value.month - 1]}"
