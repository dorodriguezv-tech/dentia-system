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
) -> str:
    parts = [soap_s or "", soap_o or "", soap_a or "", soap_p or "", free_text or ""]
    payload = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
