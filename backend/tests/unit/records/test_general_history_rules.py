"""Fase A (rediseno del expediente, docs/clinica): reglas nuevas de la Historia
Clinica General -- IMC calculado al vuelo y alertas criticas (regla 8 de
CLAUDE.md) derivadas de antecedentes patologicos personales estructurados."""

from app.modules.records import rules


def test_body_mass_index_computes_from_height_and_weight() -> None:
    # 70 kg / (1.75 m)^2 = 22.9
    assert rules.body_mass_index(1.75, 70) == 22.9


def test_body_mass_index_without_data_returns_none() -> None:
    assert rules.body_mass_index(None, 70) is None
    assert rules.body_mass_index(1.75, None) is None
    assert rules.body_mass_index(0, 70) is None


def test_pathological_history_alert_text_includes_present_disease_codes() -> None:
    text = rules.pathological_history_alert_text(
        {"diabetes": {"present": True, "evolution": "10 anos"}, "cancer": {"present": False}}
    )
    assert "diabetes" in text
    assert "cancer" not in text


def test_pathological_history_alert_text_includes_free_texts() -> None:
    text = rules.pathological_history_alert_text(
        {}, free_texts=["Hospitalizacion por hemofilia", None, ""]
    )
    assert "hemofilia" in text.lower()


def test_match_alert_keywords_on_pathological_history_text() -> None:
    text = rules.pathological_history_alert_text({"diabetes": {"present": True}})
    alerts = rules.match_alert_keywords(text, rules.CONDITION_ALERT_KEYWORDS)
    assert "Paciente con diabetes" in alerts


def test_default_catalogs_are_non_empty_tuples() -> None:
    assert "padre" in rules.FAMILY_RELATIONSHIPS
    assert "diabetes_mellitus" in rules.FAMILY_CONDITIONS
    assert "diabetes" in rules.PATHOLOGICAL_CONDITIONS
    assert "hematologico" in rules.SYSTEMS_REVIEW_SYSTEMS
    assert "anemia" in rules.SYSTEMS_REVIEW_FINDINGS_BY_SYSTEM["hematologico"]
