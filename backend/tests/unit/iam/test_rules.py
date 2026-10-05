from app.modules.iam import rules


def test_admin_clinica_requires_mfa() -> None:
    assert rules.role_requires_mfa("admin_clinica") is True


def test_odontologo_does_not_require_mfa() -> None:
    assert rules.role_requires_mfa("odontologo") is False


def test_cannot_disable_mfa_when_role_requires_it() -> None:
    assert rules.can_disable_mfa("admin_clinica") is False


def test_can_disable_mfa_when_role_does_not_require_it() -> None:
    assert rules.can_disable_mfa("recepcion") is True


def test_login_rate_limited_at_threshold() -> None:
    assert rules.is_login_rate_limited(rules.MAX_LOGIN_FAILURES) is True


def test_login_not_rate_limited_below_threshold() -> None:
    assert rules.is_login_rate_limited(rules.MAX_LOGIN_FAILURES - 1) is False
