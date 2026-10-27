"""Reglas y catalogos del expediente (antecedentes, alergias, alertas), aislados de la BD.

Catalogos configurables (CLAUDE.md sec. 7): valores por defecto razonables, a validar con
la clinica (ver docs/PENDIENTES_CLINICOS.md).
"""

from collections.abc import Iterable, Mapping
from typing import Any

HISTORY_CATEGORIES = (
    "heredofamiliar",
    "personal_patologico",
    "personal_no_patologico",
    "odontologico",
    "habito",
    "factor_riesgo",
)

SEVERITY_LEVELS = ("leve", "moderada", "severa")

# Regla 10 de CLAUDE.md: todo lo que provenga de la IA queda marcado AI_ASSISTED.
ORIGINS = ("MANUAL", "AI_ASSISTED")

# Alertas clinicas derivadas (regla 8 de CLAUDE.md): no es una tabla editable por CRUD,
# se calculan a partir de alergias activas (siempre) y de palabras clave en medicamentos
# activos / antecedentes (catalogo de abajo). Comparacion sin acentos ni mayusculas.
CONDITION_ALERT_KEYWORDS: dict[str, str] = {
    "diabetes": "Paciente con diabetes",
    "embarazo": "Paciente embarazada",
    "embarazada": "Paciente embarazada",
    "hipertension": "Paciente hipertenso",
    "marcapasos": "Paciente con marcapasos",
    "hemofilia": "Paciente con trastorno de coagulacion",
    "vih": "Paciente con VIH",
    "hepatitis": "Paciente con hepatitis",
    "epilepsia": "Paciente con epilepsia",
    "cardiopatia": "Paciente con cardiopatia",
}

MEDICATION_ALERT_KEYWORDS: dict[str, str] = {
    "anticoagulante": "Paciente usa anticoagulantes",
    "warfarina": "Paciente usa anticoagulantes (warfarina)",
    "acenocumarina": "Paciente usa anticoagulantes (acenocumarina)",
    "rivaroxaban": "Paciente usa anticoagulantes (rivaroxaban)",
    "apixaban": "Paciente usa anticoagulantes (apixaban)",
    "clopidogrel": "Paciente usa antiagregantes plaquetarios (clopidogrel)",
    "aspirina": "Paciente usa antiagregantes plaquetarios (aspirina)",
    "insulina": "Paciente usa insulina",
    "bifosfonato": "Paciente usa bifosfonatos (riesgo de osteonecrosis)",
    "corticoesteroide": "Paciente usa corticoesteroides",
    "inmunosupresor": "Paciente usa inmunosupresores",
}


def allergy_alert(substance: str, severity: str) -> str:
    if severity == "severa":
        return f"Alergia severa: {substance}"
    return f"Alergia: {substance}"


def _strip_accents(value: str) -> str:
    replacements = str.maketrans("áéíóúñ", "aeioun")
    return value.translate(replacements)


def match_alert_keywords(text: str, catalog: dict[str, str]) -> list[str]:
    """Busca palabras clave del catalogo en `text` (sin acentos, insensible a mayusculas)."""
    normalized = _strip_accents(text.lower())
    return [label for keyword, label in catalog.items() if keyword in normalized]


# --------------------------------------------------------------------------------
# Fase A (rediseno del expediente, docs/clinica): Historia Clinica General.
# Catalogos configurables (CLAUDE.md sec. 7): valores por defecto razonables a
# validar con la clinica real (ver docs/PENDIENTES_CLINICOS.md). Viven tambien en
# app/modules/catalogs (tabla clinic_catalog_items) -- estas tuplas son solo la
# documentacion/semilla por defecto, igual que HISTORY_CATEGORIES arriba.
# --------------------------------------------------------------------------------

FAMILY_RELATIONSHIPS = (
    "padre",
    "madre",
    "hermano_a",
    "abuelo_paterno",
    "abuela_paterna",
    "abuelo_materno",
    "abuela_materna",
)

FAMILY_STATUSES = ("en_vida", "fallecido")

FAMILY_CONDITIONS = (
    "diabetes_mellitus",
    "hipertension",
    "enfermedades_renales",
    "ets",
    "hepatitis_abc",
    "cancer",
    "epilepsia",
    "tuberculosis",
    "cardiopatias",
    "artritis",
    "malformaciones",
    "discapacidad_fisica",
    "padecimientos_psicologicos",
    "alcoholismo",
    "tabaquismo",
    "aparentemente_sano",
)

PATHOLOGICAL_CONDITIONS = (
    "diabetes",
    "hipertension",
    "enfermedades_renales",
    "ets",
    "hepatitis",
    "cancer",
    "epilepsia",
    "tuberculosis",
    "cardiopatias",
    "artritis",
    "malformaciones",
    "discapacidad_fisica",
    "padecimientos_psicologicos",
    "depresion",
    "varicela",
    "viruela",
    "otro",
)

BLEEDING_GUMS_LEVELS = ("nunca", "algunas_veces", "siempre")

FOOD_QUALITY_LEVELS = ("buena", "mala", "regular")

HEALTH_COVERAGE_TYPES = ("civil", "derechohabiente", "militar")

# Correccion Fase A: ya no son el unico valor valido (el campo es texto libre
# en schemas.py) -- son solo las opciones sugeridas que ofrece el formulario,
# mas "Otro" con texto a teclear.
MARITAL_STATUSES = ("soltero", "casado", "union_libre", "divorciado", "viudo")

GLUCOSE_TIMINGS = ("postprandial", "preprandial")

PATIENT_ATTITUDES = ("cooperador", "no_cooperador")

# Aparatos y sistemas del interrogatorio (SystemsReviewEntry): los que tienen
# padecimientos sí/no/evolucion con catalogo administrable
# (catalog_type="systems_review_finding", extra.system = uno de estos).
SYSTEMS_REVIEW_SYSTEMS = (
    "hematologico",
    "cardiovascular",
    "neurologico",
    "endocrino",
    "respiratorio",
    "genitourinario",
)

SYSTEMS_REVIEW_FINDINGS_BY_SYSTEM: dict[str, tuple[str, ...]] = {
    "hematologico": ("anemia", "hemorragias_frecuentes", "transfusiones"),
    "cardiovascular": ("hipertension", "soplo_cardiaco", "fiebre_reumatica", "arritmias"),
    "neurologico": ("convulsiones", "desmayos", "migrana", "paralisis"),
    "endocrino": ("diabetes", "trastornos_tiroideos", "trastornos_crecimiento"),
    "respiratorio": ("asma", "bronquitis", "tuberculosis", "sinusitis"),
    "genitourinario": ("infecciones_urinarias", "insuficiencia_renal", "calculos_renales"),
}


def body_mass_index(height_m: float | None, weight_kg: float | None) -> float | None:
    """IMC = peso / estatura^2 -- se calcula al vuelo (no se persiste en VitalSigns,
    evita datos derivados desincronizados, ver records/models.py)."""
    if not height_m or not weight_kg or height_m <= 0:
        return None
    return round(weight_kg / (height_m**2), 1)


def pathological_history_alert_text(
    diseases: Mapping[str, Any], free_texts: Iterable[str | None] = ()
) -> str:
    """Regla 8 de CLAUDE.md: las alertas criticas tambien deben salir de las
    tablas estructuradas nuevas, no solo del texto libre de MedicalHistory.
    Concatena los codigos de enfermedad marcados `present` en `diseases`
    (PersonalPathologicalHistory) junto con los textos libres del mismo
    renglon, para reusar `match_alert_keywords` tal cual."""
    present_codes = [
        code
        for code, info in diseases.items()
        if isinstance(info, Mapping) and bool(info.get("present"))
    ]
    texts = [t for t in free_texts if t]
    return " ".join([*present_codes, *texts])
