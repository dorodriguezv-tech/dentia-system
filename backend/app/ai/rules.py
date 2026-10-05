"""Catalogos y reglas del asistente de IA (docs/03_AGENTE_IA_VOZ.md), aislados de la BD.

Catalogo configurable (CLAUDE.md sec. 7): valores por defecto razonables, a validar
con la clinica (ver docs/PENDIENTES_CLINICOS.md).
"""

ACTION_TYPES: tuple[str, ...] = (
    "set_chief_complaint",
    "add_allergy",
    "add_medication",
    "add_medical_history",
    "add_vital_signs",
    "add_tooth_finding",
    "add_planned_procedure",
    "add_performed_procedure",
    "add_diagnosis",
    "append_note",
    "schedule_followup",
)

STATUSES: tuple[str, ...] = ("PENDING", "ACCEPTED", "REJECTED")

# Regla 9 de CLAUDE.md: la IA nunca escribe directamente ni puede finalizar/firmar
# notas, borrar, recetar, cobrar o cambiar datos de identidad. Si el modelo de Ollama
# devuelve un "type" que coincide con alguno de estos (alucinado o fuera del esquema
# declarado), se descarta y se registra en vez de crear una sugerencia (ver interpreter.py).
PROHIBITED_ACTION_TYPES: frozenset[str] = frozenset(
    {
        "finalize_note",
        "sign_note",
        "sign_document",
        "delete_record",
        "delete",
        "prescribe",
        "prescribe_medication",
        "create_payment",
        "register_payment",
        "charge_payment",
        "change_identity",
        "change_patient_identity",
    }
)


def is_editable(status: str) -> bool:
    """Solo una sugerencia PENDING se puede aceptar o rechazar."""
    return status == "PENDING"
