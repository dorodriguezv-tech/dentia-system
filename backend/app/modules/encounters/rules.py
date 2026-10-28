"""Maquina de estados de la nota clinica (regla 1 de CLAUDE.md), aislada de la BD."""

import hashlib

NOTE_STATUSES = ("DRAFT", "FINAL", "CORRECTED", "CANCELLED")

# Estados: DRAFT -> FINAL -> (CORRECTED | CANCELLED). DRAFT tambien se puede cancelar
# (anular un borrador que no se va a usar) sin pasar por FINAL.
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"FINAL", "CANCELLED"},
    "FINAL": {"CORRECTED", "CANCELLED"},
    "CORRECTED": set(),
    "CANCELLED": set(),
}


def can_transition(current: str, target: str) -> bool:
    return target in _ALLOWED_TRANSITIONS.get(current, set())


def is_editable(status: str) -> bool:
    """Solo una nota DRAFT se puede editar (regla 1: una nota FINAL no se modifica)."""
    return status == "DRAFT"


def compute_content_hash(
    soap_s: str | None,
    soap_o: str | None,
    soap_a: str | None,
    soap_p: str | None,
    free_text: str | None,
    *,
    interrogatorio: str | None = None,
    medicamentos: str | None = None,
    estudios_radiograficos: str | None = None,
    descripcion_procedimiento: str | None = None,
    pronostico_evolucion: str | None = None,
    indicaciones: str | None = None,
    plan_proxima_cita: str | None = None,
    fecha_proxima_cita: str | None = None,
    evaluacion_actualizacion: str | None = None,
) -> str:
    # Fase D: los campos nuevos de la nota de evolucion tambien entran al hash
    # de integridad (regla 1 de CLAUDE.md) -- si se agregan/corrigen despues,
    # es a traves del mismo flujo de correccion, nunca sobrescribiendo una
    # version FINAL.
    parts = [
        soap_s or "",
        soap_o or "",
        soap_a or "",
        soap_p or "",
        free_text or "",
        interrogatorio or "",
        medicamentos or "",
        estudios_radiograficos or "",
        descripcion_procedimiento or "",
        pronostico_evolucion or "",
        indicaciones or "",
        plan_proxima_cita or "",
        fecha_proxima_cita or "",
        evaluacion_actualizacion or "",
    ]
    payload = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
