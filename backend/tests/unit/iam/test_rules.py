from app.modules.iam import rules


def test_admin_clinica_does_not_require_mfa_while_disabled() -> None:
    # MFA_REQUIRED_ROLES esta vacio temporalmente (ver rules.py) -- cuando se
    # reactive, este caso vuelve a ser True para "admin_clinica".
    assert rules.role_requires_mfa("admin_clinica") is False


def test_odontologo_does_not_require_mfa() -> None:
    assert rules.role_requires_mfa("odontologo") is False


def test_can_disable_mfa_for_any_role_while_requirement_is_disabled() -> None:
    assert rules.can_disable_mfa("admin_clinica") is True


def test_can_disable_mfa_when_role_does_not_require_it() -> None:
    assert rules.can_disable_mfa("recepcion") is True


def test_login_rate_limited_at_threshold() -> None:
    assert rules.is_login_rate_limited(rules.MAX_LOGIN_FAILURES) is True


def test_login_not_rate_limited_below_threshold() -> None:
    assert rules.is_login_rate_limited(rules.MAX_LOGIN_FAILURES - 1) is False
