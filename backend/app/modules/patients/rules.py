"""Reglas de negocio del modulo patients, aisladas de la base de datos."""

from datetime import date

STATUS_CODES = ("activo", "inactivo", "referido", "fallecido", "bloqueado")
DEFAULT_STATUS = "activo"

CONTACT_ROLES = ("guardian", "emergency", "other")

# Catalogo de tipo de paciente (anotacion del expediente, pendiente #73 de
# docs/PENDIENTES_CLINICOS.md): distingue pediatrico/adulto para la Historia
# Clinica correspondiente (ver patients/PediatricHistoryTab.tsx vs. el resto).
# Es editable a mano (no 100% derivado): se calcula por defecto a partir de
# `date_of_birth` solo cuando el usuario no lo especifica explicitamente al
# crear o actualizar el paciente (patients/service.py).
PATIENT_TYPE_PEDIATRIC = "pediatrico"
PATIENT_TYPE_ADULT = "adulto"
PATIENT_TYPE_CODES = (PATIENT_TYPE_PEDIATRIC, PATIENT_TYPE_ADULT)

# Corte clinico por defecto para distinguir odontologia pediatrica de general.
# 12 anios es un corte comun (erupcion de la denticion permanente casi
# completa, salvo terceros molares) pero no esta validado con la clinica real
# -- ver pendiente #73 de docs/PENDIENTES_CLINICOS.md.
PEDIATRIC_AGE_CUTOFF_YEARS = 12

# "Edicion controlada" (Fase 3): un cambio de estado del paciente debe traer un motivo,
# para quedar trazado igual que cualquier otro cambio administrativo relevante.
STATUS_CHANGE_REQUIRES_REASON = True

DUPLICATE_NAME_SIMILARITY_THRESHOLD = 0.4

# Fase 12.1 (correccion A2): umbral de tolerancia a errores de captura para la
# busqueda global (palabra contra palabra, no el nombre completo contra el nombre
# completo) -- deliberadamente distinto de DUPLICATE_NAME_SIMILARITY_THRESHOLD, que
# sigue siendo solo para check_duplicates. similarity('peres','perez') = 0.5 (un
# error de una letra); similarity('gonzalez','perez') = 0.07 (nombre no relacionado).
SEARCH_WORD_FUZZY_THRESHOLD = 0.45


def calculate_age(date_of_birth: date, *, as_of: date | None = None) -> int:
    reference = as_of or date.today()
    age = reference.year - date_of_birth.year
    had_birthday = (reference.month, reference.day) >= (date_of_birth.month, date_of_birth.day)
    if not had_birthday:
        age -= 1
    return max(age, 0)


def calculate_patient_type(date_of_birth: date, *, as_of: date | None = None) -> str:
    """Calcula pediatrico/adulto a partir de la edad (ver PEDIATRIC_AGE_CUTOFF_YEARS).

    Reutiliza `calculate_age` -- no duplica el calculo de edad. Es solo el
    valor por DEFECTO: patients/service.py lo usa unicamente cuando el
    `patient_type` no viene explicito en el payload de alta/edicion.
    """
    age = calculate_age(date_of_birth, as_of=as_of)
    return PATIENT_TYPE_PEDIATRIC if age < PEDIATRIC_AGE_CUTOFF_YEARS else PATIENT_TYPE_ADULT


def build_full_name(
    first_name: str, last_name_paternal: str, last_name_maternal: str | None
) -> str:
    parts = [first_name, last_name_paternal, last_name_maternal or ""]
    return " ".join(p.strip() for p in parts if p.strip())
