from app.modules.records import rules


def test_match_alert_keywords_finds_condition() -> None:
    alerts = rules.match_alert_keywords(
        "Paciente con diabetes tipo 2", rules.CONDITION_ALERT_KEYWORDS
    )
    assert "Paciente con diabetes" in alerts


def test_match_alert_keywords_is_accent_and_case_insensitive() -> None:
    alerts = rules.match_alert_keywords(
        "EMBARAZO confirmado por laboratorio", rules.CONDITION_ALERT_KEYWORDS
    )
    assert "Paciente embarazada" in alerts


def test_match_alert_keywords_no_match_returns_empty() -> None:
    assert (
        rules.match_alert_keywords("Sin antecedentes relevantes", rules.CONDITION_ALERT_KEYWORDS)
        == []
    )


def test_match_alert_keywords_medication() -> None:
    alerts = rules.match_alert_keywords("Warfarina 5mg", rules.MEDICATION_ALERT_KEYWORDS)
    assert any("anticoagulantes" in a for a in alerts)


def test_allergy_alert_severe() -> None:
    assert rules.allergy_alert("Penicilina", "severa") == "Alergia severa: Penicilina"


def test_allergy_alert_mild() -> None:
    assert rules.allergy_alert("Penicilina", "leve") == "Alergia: Penicilina"
