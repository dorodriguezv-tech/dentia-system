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

# Fase 12 (temporal): MFA deshabilitada por completo a peticion del dueno del
# proyecto -- ni se exige configurarla por rol, ni se le vuelve a pedir el codigo a
# una cuenta que ya la tenia activa (p.ej. el admin sembrado por app.seed). Solo
# requiere reiniciar el backend: no toca la base de datos, asi que una cuenta que ya
# tenia MFA configurada (mfa_enabled/mfa_secret) la recupera tal cual al reactivar
# esta bandera. CLAUDE.md sec. 5 exige MFA para admin_clinica -- para reactivarla,
# MFA_ENABLED = True.
MFA_ENABLED = False

MFA_REQUIRED_ROLES = frozenset({"admin_clinica"})

MAX_LOGIN_FAILURES = 5
LOGIN_LOCKOUT_WINDOW_MINUTES = 15


def role_requires_mfa(role_code: str) -> bool:
    return MFA_ENABLED and role_code in MFA_REQUIRED_ROLES


def can_disable_mfa(role_code: str) -> bool:
    return not role_requires_mfa(role_code)


def is_login_rate_limited(recent_failed_attempts: int) -> bool:
    return recent_failed_attempts >= MAX_LOGIN_FAILURES
