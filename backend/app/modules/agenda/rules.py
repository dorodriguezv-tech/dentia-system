"""Catalogos y reglas de la agenda (docs/02 sec. 4), aisladas de la BD.

Catalogos configurables (CLAUDE.md sec. 7): valores por defecto razonables, a validar
con la clinica (ver docs/PENDIENTES_CLINICOS.md).
"""

APPOINTMENT_STATUSES = (
    "RESERVADA",
    "CONFIRMADA",
    "EN_SALA",
    "EN_ATENCION",
    "TERMINADA",
    "CANCELADA",
    "NO_SHOW",
    "REPROGRAMADA",
)

# RESERVADA/CONFIRMADA pueden saltar directo a EN_ATENCION (botón "Iniciar atención"):
# EN_SALA es un paso opcional de sala de espera, no obligatorio para cada cita.
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "RESERVADA": {"CONFIRMADA", "EN_SALA", "EN_ATENCION", "CANCELADA", "NO_SHOW", "REPROGRAMADA"},
    "CONFIRMADA": {"EN_SALA", "EN_ATENCION", "CANCELADA", "NO_SHOW", "REPROGRAMADA"},
    "EN_SALA": {"EN_ATENCION", "CANCELADA", "NO_SHOW"},
    "EN_ATENCION": {"TERMINADA"},
    "TERMINADA": set(),
    "CANCELADA": set(),
    "NO_SHOW": set(),
    "REPROGRAMADA": set(),
}

# Estados en los que una cita todavia ocupa su horario (para el calculo de traslapes).
ACTIVE_STATUSES = ("RESERVADA", "CONFIRMADA", "EN_SALA", "EN_ATENCION")

# Transiciones que exigen motivo (igual que la anulacion de registros clinicos, regla 2).
REASON_REQUIRED_STATUSES = ("CANCELADA", "NO_SHOW")


def can_transition(current: str, target: str) -> bool:
    return target in _ALLOWED_TRANSITIONS.get(current, set())


def is_editable(status: str) -> bool:
    """Una cita se puede reprogramar o editar mientras no haya pasado de RESERVADA/CONFIRMADA."""
    return status in ("RESERVADA", "CONFIRMADA")


# Catalogo provisional de tipos de cita, solo para sugerir una duracion por defecto.
# Se debe unificar con el catalogo real de procedimientos y precios de la Fase 7
# (ver pendiente en docs/PENDIENTES_CLINICOS.md).
APPOINTMENT_TYPES: dict[str, dict[str, object]] = {
    "consulta": {"label": "Consulta / valoracion", "default_minutes": 30},
    "limpieza": {"label": "Limpieza dental", "default_minutes": 45},
    "restauracion": {"label": "Restauracion (resina/amalgama)", "default_minutes": 60},
    "endodoncia": {"label": "Endodoncia", "default_minutes": 90},
    "extraccion": {"label": "Extraccion", "default_minutes": 45},
    "ortodoncia_control": {"label": "Control de ortodoncia", "default_minutes": 20},
    "protesis": {"label": "Protesis", "default_minutes": 60},
    "urgencia": {"label": "Urgencia", "default_minutes": 30},
}
APPOINTMENT_TYPE_CODES: tuple[str, ...] = tuple(APPOINTMENT_TYPES.keys())


def default_duration_minutes(appointment_type: str) -> int:
    minutes = APPOINTMENT_TYPES[appointment_type]["default_minutes"]
    assert isinstance(minutes, int)
    return minutes


# Recordatorios (CLAUDE.md Fase 6): por ahora solo se registran como tarea pendiente,
# el envio real queda fuera de alcance. "24h_antes" es el unico tipo por ahora.
REMINDER_KINDS = ("24h_antes",)
