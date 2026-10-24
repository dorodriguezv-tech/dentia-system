"""Politica de contrasenas (Fase "Publicacion en Hostinger" sec. 6, cambio #1):
sin MFA, la contrasena es la unica barrera de cada cuenta.

Verificacion contra brechas conocidas (estilo "Have I Been Pwned") no es posible
aqui: la red `app` de produccion (docker-compose.yml) es interna, sin salida a
internet, a proposito (si alguien comprometiera la API no podria abrir
conexiones hacia afuera). Por eso el rechazo de contrasenas comunes/filtradas
usa una lista estatica empaquetada con la imagen, no una consulta externa.
"""

from functools import lru_cache
from pathlib import Path

MIN_PASSWORD_LENGTH = 12
PASSWORD_HISTORY_SIZE = 5

_COMMON_PASSWORDS_FILE = Path(__file__).parent / "common_passwords.txt"


@lru_cache
def _common_passwords() -> frozenset[str]:
    lines = _COMMON_PASSWORDS_FILE.read_text(encoding="utf-8").splitlines()
    return frozenset(line.strip().lower() for line in lines if line.strip())


def password_policy_violations(password: str) -> list[str]:
    """Lista de mensajes de violacion (vacia = la contrasena cumple la politica)."""
    violations = []
    if len(password) < MIN_PASSWORD_LENGTH:
        violations.append(f"La contrasena debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")
    if password.lower() in _common_passwords():
        violations.append("Esa contrasena es demasiado comun o aparece en filtraciones conocidas.")
    return violations


def is_password_strong(password: str) -> bool:
    return not password_policy_violations(password)
