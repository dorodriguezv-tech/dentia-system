"""Catalogos y reglas de plantillas/consentimientos, aislados de la BD.

Catalogo configurable (CLAUDE.md sec. 7): valores por defecto razonables, a validar con
la clinica (ver docs/PENDIENTES_CLINICOS.md).

Los 24 codigos reales (`TEMPLATE_CODES`) son los formatos oficiales de
docs/formatos/ (consentimientos informados + aviso de privacidad + cartas),
integrados segun el plan aprobado (ver pendiente nuevo en
docs/PENDIENTES_CLINICOS.md). Reemplazan a los 4 codigos de ejemplo
("general"/"extraccion"/"endodoncia"/"anestesia") que existian antes de esa
integracion -- esos 4 se retiran (no se borran, ver
service.py::retire_legacy_example_templates) pero YA NO forman parte de este
catalogo: un `Consent` antiguo que los use sigue viendose igual por su
`template_id` directo, sin depender de que el codigo siga aqui.
"""

import html
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

# categoria -> como se agrupan en el selector de la pestaña Consentimientos
# (frontend/src/modules/documents/catalog.ts duplica estas 3 categorias y esta
# lista de codigos, igual criterio ya usado para TEMPLATE_CODE_LABELS).
TEMPLATE_CATEGORIES: dict[str, str] = {
    "protesis_fija": "consentimiento",
    "aplicacion_fluor": "consentimiento",
    "anestesia_local_oral": "consentimiento",
    "exodoncia": "consentimiento",
    "incrustacion_dental": "consentimiento",
    "obturacion_dental": "consentimiento",
    "endodoncia": "consentimiento",
    "protesis_removible": "consentimiento",
    "sellado_fosetas_fisuras": "consentimiento",
    "toma_radiografias": "consentimiento",
    "limpieza_dental": "consentimiento",
    "aplicacion_fluor_pediatrico": "consentimiento",
    "anestesia_local_pediatrico": "consentimiento",
    "corona_metalica_pediatrico": "consentimiento",
    "sellado_fosetas_pediatrico": "consentimiento",
    "obturacion_resina_pediatrico": "consentimiento",
    "profilaxis_pediatrico": "consentimiento",
    "toma_radiografias_pediatrico": "consentimiento",
    "tratamiento_pulpar_pediatrico": "consentimiento",
    "aviso_privacidad": "aviso_privacidad",
    "carta_tratamiento_concluido": "carta",
    "carta_tratamiento_suspendido": "carta",
    "carta_autorizacion_uso_imagen": "carta",
    "carta_caso_medico_legal": "carta",
}

TEMPLATE_CODES: tuple[str, ...] = tuple(TEMPLATE_CATEGORIES.keys())

TEMPLATE_CATEGORY_LABELS: dict[str, str] = {
    "consentimiento": "Consentimientos informados",
    "aviso_privacidad": "Avisos de privacidad",
    "carta": "Cartas",
}

SIGNER_RELATIONSHIPS: tuple[str, ...] = ("paciente", "tutor", "otro")

# Los 4 codigos de ejemplo que existian antes de integrar los 24 formatos reales
# ("Ejemplo -- validar con la clinica", ver el viejo app/seed.py). Se retiran
# los 4 (is_current=False, sin version nueva, ver
# service.py::retire_legacy_example_templates) ANTES de sembrar los reales:
# "endodoncia" es tambien uno de los 24 codigos reales (ahora el "Procedimiento
# endodontico" real de docs/formatos) -- al quedar sin version `is_current`,
# seed_default_document_templates lo detecta como "falta sembrar" y crea la
# version 2 real sobre esa version 1 de ejemplo ya retirada, por el versionado
# normal (create_template_version). Los otros 3 quedan retirados sin
# reemplazo, ya que no tienen un formato real equivalente en este catalogo.
LEGACY_EXAMPLE_TEMPLATE_CODES: tuple[str, ...] = (
    "general",
    "extraccion",
    "endodoncia",
    "anestesia",
)


@dataclass(frozen=True)
class ExtraFieldSpec:
    """Un dato libre que un formato pide y que no es derivable del expediente
    (ver documents/service.py::build_consent_prefill). `key` es la ruta que se
    sustituye en la plantilla como `{{extra.<key>}}` (rules.py::render_template)."""

    key: str
    label: str
    required: bool
    multiline: bool = False


# Solo los codigos listados aqui piden algo mas que paciente/profesional/
# clinica/fecha/testigos -- el resto (~18 de 24) no aparece en este dict y por
# lo tanto no muestra ninguna seccion de "datos adicionales" en el frontend
# (ver plan aprobado, punto 5: simplificar el menu).
TEMPLATE_EXTRA_FIELDS: dict[str, tuple[ExtraFieldSpec, ...]] = {
    **{
        code: (
            ExtraFieldSpec(
                key="tutor_parentesco",
                label="Parentesco del tutor/responsable con el paciente",
                required=True,
            ),
        )
        for code in TEMPLATE_CATEGORIES
        if code.endswith("_pediatrico")
    },
    "protesis_fija": (
        ExtraFieldSpec(key="tipo_protesis", label="Tipo de prótesis a colocar", required=True),
    ),
    "protesis_removible": (
        ExtraFieldSpec(key="tipo_protesis", label="Tipo de prótesis a colocar", required=True),
    ),
    "exodoncia": (
        ExtraFieldSpec(
            key="riesgos_adicionales",
            label="Riesgos adicionales propios de este caso (opcional)",
            required=False,
            multiline=True,
        ),
    ),
    "carta_tratamiento_concluido": (
        ExtraFieldSpec(
            key="tratamiento_nombre", label="Nombre del tratamiento concluido", required=False
        ),
        ExtraFieldSpec(key="grupo_pedagogico", label="Grupo/área (opcional)", required=False),
    ),
    "carta_tratamiento_suspendido": (
        ExtraFieldSpec(
            key="motivo_suspension", label="Motivo de la suspensión", required=True, multiline=True
        ),
        ExtraFieldSpec(
            key="riesgos_explicados",
            label="Riesgos y consecuencias explicados al paciente",
            required=True,
            multiline=True,
        ),
    ),
    "carta_caso_medico_legal": (
        ExtraFieldSpec(key="diagnostico", label="Diagnóstico", required=False, multiline=True),
        ExtraFieldSpec(
            key="reporte_lesiones", label="Reporte de las lesiones", required=True, multiline=True
        ),
        ExtraFieldSpec(
            key="acto_notificado", label="Acto notificado", required=True, multiline=True
        ),
    ),
}

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
