"""Reglas y catalogos del plan de tratamiento (docs/02 sec. 4; reglas 3 y 4 de
CLAUDE.md), aisladas de la BD."""

PLAN_STATUSES = ("BORRADOR", "PRESENTADO", "ACEPTADO", "RECHAZADO", "EN_PROGRESO", "TERMINADO")

_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "BORRADOR": {"PRESENTADO"},
    "PRESENTADO": {"ACEPTADO", "RECHAZADO"},
    "ACEPTADO": {"EN_PROGRESO"},
    "RECHAZADO": set(),
    "EN_PROGRESO": {"TERMINADO"},
    "TERMINADO": set(),
}


def can_transition(current: str, target: str) -> bool:
    return target in _ALLOWED_TRANSITIONS.get(current, set())


def is_editable(status: str) -> bool:
    """Fases e items solo se agregan/anulan mientras el plan sigue en borrador."""
    return status == "BORRADOR"


PRIORITIES = ("alta", "media", "baja")
ACCEPTANCE_TYPES = ("TOTAL", "PARCIAL")

# Catalogo provisional de tipos de cita de la Fase 6 (agenda/rules.py); el catalogo de
# PROCEDIMIENTOS real de esta fase vive en la tabla procedure_catalog (editable por
# sucursal, a diferencia de los catalogos Python usados en fases anteriores) porque
# trae precios que varian por clinica -- ver docs/02_ARQUITECTURA.md sec. 5.7.
