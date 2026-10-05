from app.modules.treatment import rules


def test_borrador_solo_avanza_a_presentado() -> None:
    assert rules.can_transition("BORRADOR", "PRESENTADO") is True
    assert rules.can_transition("BORRADOR", "ACEPTADO") is False


def test_presentado_puede_aceptarse_o_rechazarse() -> None:
    assert rules.can_transition("PRESENTADO", "ACEPTADO") is True
    assert rules.can_transition("PRESENTADO", "RECHAZADO") is True


def test_aceptado_solo_avanza_a_en_progreso() -> None:
    assert rules.can_transition("ACEPTADO", "EN_PROGRESO") is True
    assert rules.can_transition("ACEPTADO", "TERMINADO") is False


def test_en_progreso_solo_avanza_a_terminado() -> None:
    assert rules.can_transition("EN_PROGRESO", "TERMINADO") is True


def test_estados_terminales_no_tienen_transiciones() -> None:
    for status in ("RECHAZADO", "TERMINADO"):
        assert rules.can_transition(status, "BORRADOR") is False
        assert rules.can_transition(status, "PRESENTADO") is False


def test_is_editable_solo_en_borrador() -> None:
    assert rules.is_editable("BORRADOR") is True
    assert rules.is_editable("PRESENTADO") is False
    assert rules.is_editable("ACEPTADO") is False
