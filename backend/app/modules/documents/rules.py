"""Catalogos y reglas de plantillas/consentimientos, aislados de la BD.

Catalogo configurable (CLAUDE.md sec. 7): valores por defecto razonables, a validar con
la clinica (ver docs/PENDIENTES_CLINICOS.md).
"""

import html
import re
from collections.abc import Mapping
from typing import Any

TEMPLATE_CODES: tuple[str, ...] = ("general", "extraccion", "endodoncia", "anestesia")

SIGNER_RELATIONSHIPS: tuple[str, ...] = ("paciente", "tutor", "otro")

_VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}")


def _lookup(variables: Mapping[str, Any], path: str) -> Any:
    value: Any = variables
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return ""
        value = value[part]
    return value


def render_template(html_content: str, variables: Mapping[str, Any]) -> str:
    """Sustituye {{paciente.nombre}}, {{procedimiento}}, etc. (docs/09 -- plantillas en
    HTML con variables). No es un motor de plantillas completo (sin condicionales, sin
    expresiones): es una sustitucion literal de rutas conocidas, a proposito, para que una
    plantilla editable por la clinica no pueda ejecutar nada mas que texto. Cada valor se
    escapa con html.escape para no romper la estructura del documento si el dato real
    (p.ej. el nombre de un paciente) contiene caracteres como `<` o `&`."""

    def _replace(match: re.Match[str]) -> str:
        value = _lookup(variables, match.group(1))
        return html.escape(str(value)) if value != "" else ""

    return _VARIABLE_PATTERN.sub(_replace, html_content)
