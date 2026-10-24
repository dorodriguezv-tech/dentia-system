from app.core.password_policy import (
    MIN_PASSWORD_LENGTH,
    is_password_strong,
    password_policy_violations,
)


def test_rejects_passwords_shorter_than_the_minimum() -> None:
    short = "a" * (MIN_PASSWORD_LENGTH - 1)
    violations = password_policy_violations(short)
    assert any("al menos" in v for v in violations)


def test_accepts_a_long_enough_uncommon_password() -> None:
    assert is_password_strong("Xk9#mPlq7!vZ2wQr")


def test_rejects_a_common_password_even_if_long_enough() -> None:
    violations = password_policy_violations("password1234")
    assert any("comun" in v for v in violations)


def test_common_password_check_is_case_insensitive() -> None:
    violations = password_policy_violations("PASSWORD1234")
    assert any("comun" in v for v in violations)


def test_exactly_at_the_minimum_length_is_not_a_length_violation() -> None:
    password = "Zx8#mQprUvWy"  # 12 chars, not in the common list
    assert len(password) == MIN_PASSWORD_LENGTH
    violations = password_policy_violations(password)
    assert not any("al menos" in v for v in violations)
