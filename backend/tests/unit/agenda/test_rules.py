from app.modules.agenda import rules


def test_reservada_puede_pasar_a_confirmada_en_sala_o_en_atencion() -> None:
    assert rules.can_transition("RESERVADA", "CONFIRMADA") is True
    assert rules.can_transition("RESERVADA", "EN_SALA") is True
    assert rules.can_transition("RESERVADA", "EN_ATENCION") is True


def test_reservada_o_confirmada_pueden_cancelarse_o_marcarse_no_show() -> None:
    for origin in ("RESERVADA", "CONFIRMADA"):
        assert rules.can_transition(origin, "CANCELADA") is True
        assert rules.can_transition(origin, "NO_SHOW") is True
        assert rules.can_transition(origin, "REPROGRAMADA") is True


def test_en_sala_solo_avanza_a_en_atencion_o_se_cancela() -> None:
    assert rules.can_transition("EN_SALA", "EN_ATENCION") is True
    assert rules.can_transition("EN_SALA", "RESERVADA") is False


def test_en_atencion_solo_avanza_a_terminada() -> None:
    assert rules.can_transition("EN_ATENCION", "TERMINADA") is True
    assert rules.can_transition("EN_ATENCION", "CANCELADA") is False


def test_estados_terminales_no_tienen_transiciones() -> None:
    for status in ("TERMINADA", "CANCELADA", "NO_SHOW", "REPROGRAMADA"):
        assert rules.can_transition(status, "CONFIRMADA") is False
        assert rules.can_transition(status, "RESERVADA") is False


def test_cancelada_y_no_show_exigen_motivo() -> None:
    assert rules.REASON_REQUIRED_STATUSES == ("CANCELADA", "NO_SHOW")


def test_is_editable_solo_reservada_y_confirmada() -> None:
    assert rules.is_editable("RESERVADA") is True
    assert rules.is_editable("CONFIRMADA") is True
    assert rules.is_editable("EN_SALA") is False
    assert rules.is_editable("TERMINADA") is False


def test_default_duration_minutes() -> None:
    assert rules.default_duration_minutes("consulta") == 30
    assert rules.default_duration_minutes("endodoncia") == 90
