"""Reglas de negocio del modulo patients, aisladas de la base de datos."""

from datetime import date

STATUS_CODES = ("activo", "inactivo", "referido", "fallecido", "bloqueado")
DEFAULT_STATUS = "activo"

CONTACT_ROLES = ("guardian", "emergency", "other")

# "Edicion controlada" (Fase 3): un cambio de estado del paciente debe traer un motivo,
# para quedar trazado igual que cualquier otro cambio administrativo relevante.
STATUS_CHANGE_REQUIRES_REASON = True

DUPLICATE_NAME_SIMILARITY_THRESHOLD = 0.4


def calculate_age(date_of_birth: date, *, as_of: date | None = None) -> int:
    reference = as_of or date.today()
    age = reference.year - date_of_birth.year
    had_birthday = (reference.month, reference.day) >= (date_of_birth.month, date_of_birth.day)
    if not had_birthday:
        age -= 1
    return max(age, 0)


def build_full_name(
    first_name: str, last_name_paternal: str, last_name_maternal: str | None
) -> str:
    parts = [first_name, last_name_paternal, last_name_maternal or ""]
    return " ".join(p.strip() for p in parts if p.strip())
