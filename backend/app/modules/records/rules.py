"""Reglas y catalogos del expediente (antecedentes, alergias, alertas), aislados de la BD.

Catalogos configurables (CLAUDE.md sec. 7): valores por defecto razonables, a validar con
la clinica (ver docs/PENDIENTES_CLINICOS.md).
"""

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
