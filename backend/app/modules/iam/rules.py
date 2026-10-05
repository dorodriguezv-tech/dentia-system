"""Reglas de negocio de IAM, aisladas de la base de datos para poder probarlas directo."""

ROLE_CODES = (
    "superadmin",
    "admin_clinica",
    "odontologo",
    "especialista",
    "asistente",
    "recepcion",
    "caja",
)

MFA_REQUIRED_ROLES = frozenset({"admin_clinica"})

MAX_LOGIN_FAILURES = 5
LOGIN_LOCKOUT_WINDOW_MINUTES = 15


def role_requires_mfa(role_code: str) -> bool:
    return role_code in MFA_REQUIRED_ROLES


def can_disable_mfa(role_code: str) -> bool:
    return not role_requires_mfa(role_code)


def is_login_rate_limited(recent_failed_attempts: int) -> bool:
    return recent_failed_attempts >= MAX_LOGIN_FAILURES
