"""Fase C (rediseno del expediente, docs/clinica): reglas de la Historia
Clinica Odontologica -- catalogos por defecto y validacion de piezas FDI
permanentes para diagnostico/plan de tratamiento por organo dental."""

from app.modules.odontological_history import rules


def test_default_catalogs_are_non_empty_tuples() -> None:
    assert "mesocefalo" in rules.SKULL_TYPES
    assert "mesofacial" in rules.FACIAL_BIOTYPES
    assert "I" in rules.KENNEDY_CLASSES
    assert "si" in rules.PERIODONTAL_ANAMNESIS_ANSWER_VALUES
    assert "buena" in rules.ORAL_HEALTH_SELF_PERCEPTION_LEVELS
    assert "hallazgos" in rules.RADIOGRAPHIC_FINDING_TYPES


def test_periodontal_anamnesis_has_30_literal_questions() -> None:
    # Nota de discrepancia documentada en rules.py: la especificacion menciona
    # "32 preguntas" pero enumera explicitamente 30 codigos (la pregunta 1 del
    # PDF original se reparte en 3 sub-respuestas). Se siguio la lista literal.
    assert len(rules.PERIODONTAL_ANAMNESIS_QUESTIONS) == 30
    assert len(rules.PERIODONTAL_ANAMNESIS_QUESTION_CODES) == 30
    assert "sensibilidad_frio" in rules.PERIODONTAL_ANAMNESIS_QUESTION_CODES
    assert "otro_habito_dano" in rules.PERIODONTAL_ANAMNESIS_QUESTION_CODES


def test_is_valid_permanent_tooth_code_accepts_only_permanent_fdi() -> None:
    assert rules.is_valid_permanent_tooth_code("11") is True
    assert rules.is_valid_permanent_tooth_code("48") is True
    assert rules.is_valid_permanent_tooth_code("28") is True
    # Piezas temporales (51-85) no son validas aqui -- diagnostico por organo
    # dental y analisis de protesis fija solo aplican a piezas permanentes.
    assert rules.is_valid_permanent_tooth_code("55") is False
    assert rules.is_valid_permanent_tooth_code("99") is False
    assert rules.is_valid_permanent_tooth_code("not-a-tooth") is False


def test_is_valid_tooth_code_accepts_permanent_and_temporary_fdi() -> None:
    # Fase E: el plan de tratamiento por organo dental (ToothTreatmentPlanEntry)
    # se amplio para aceptar tambien piezas temporales (plan pediatrico
    # permanente/temporal), a diferencia de is_valid_permanent_tooth_code.
    assert rules.is_valid_tooth_code("11") is True
    assert rules.is_valid_tooth_code("55") is True
    assert rules.is_valid_tooth_code("85") is True
    assert rules.is_valid_tooth_code("99") is False
    assert rules.is_valid_tooth_code("not-a-tooth") is False
