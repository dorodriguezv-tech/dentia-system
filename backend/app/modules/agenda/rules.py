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


# "Tipos de consulta/cita" (antes fijo aqui) ahora vive en el catalogo administrable
# por sucursal (B1, Fase 12.2): app/modules/catalogs, catalog_type="appointment_type".
# Ver agenda/service.py::_default_duration_minutes.
DEFAULT_APPOINTMENT_DURATION_MINUTES = 30

# Recordatorios (CLAUDE.md Fase 6): por ahora solo se registran como tarea pendiente,
# el envio real queda fuera de alcance. "24h_antes" es el unico tipo por ahora.
REMINDER_KINDS = ("24h_antes",)

# Fase 12.1 (correccion A1): roles que atienden pacientes y por lo tanto necesitan un
# Provider (entidad agendable, distinta de User desde la Fase 6) para aparecer en la
# agenda. Un Provider ya no se crea a mano: se crea/reactiva solo al dar de alta o
# promover a un usuario a uno de estos roles (ver iam/service.py), y se desactiva al
# quitarle el rol o desactivar al usuario -- nunca se borra, porque puede tener citas.
PROVIDER_ROLES = frozenset({"odontologo", "especialista"})

# Paleta rotativa para el color por defecto de un Provider nuevo (distinta de los
# colores de marca de la clinica, que son configurables aparte): solo busca que dos
# profesionales nuevos no compartan color en el calendario a simple vista.
PROVIDER_COLOR_PALETTE = (
    "#2BB3A3",
    "#4A90C2",
    "#E0A100",
    "#D64545",
    "#7B7FD4",
    "#3BA55C",
    "#F2A65A",
    "#5BBFD6",
)


def next_provider_color(existing_provider_count: int) -> str:
    return PROVIDER_COLOR_PALETTE[existing_provider_count % len(PROVIDER_COLOR_PALETTE)]
