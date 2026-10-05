"""Tipos Pydantic compartidos.

No usamos `pydantic.EmailStr` tal cual: por defecto hace una resolucion DNS
(check_deliverability) para confirmar que el dominio acepta correo, lo que
rompe el login si el servidor de la clinica no tiene salida a internet
(CLAUDE.md: la IA es local, pero el resto del sistema tambien debe operar
sin depender de servicios externos). Mantenemos la validacion de formato
pero sin la resolucion DNS.
"""

from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from pydantic import BeforeValidator


def _normalize_email(value: str) -> str:
    try:
        result = validate_email(value, check_deliverability=False)
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc
    return result.normalized


Email = Annotated[str, BeforeValidator(_normalize_email)]
