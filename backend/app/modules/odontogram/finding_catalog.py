"""Catalogo de hallazgos del odontograma: color y simbolo por codigo.

Catalogo configurable (CLAUDE.md sec. 7): valores por defecto razonables, a validar
con la clinica (ver docs/PENDIENTES_CLINICOS.md). Fuente de verdad unica para los
codigos, etiquetas y simbolos: frontend/src/modules/odontogram/findingCatalog.ts es
una copia para la UI, igual que el patron ya usado con los presets de marca y el
catalogo de permisos de IAM. El color de cada hallazgo aqui es solo informativo (para
un futuro render del lado del servidor, p.ej. el PDF de Fase 7): el frontend NUNCA usa
este hex directamente (CLAUDE.md sec. 6), sino las variables --color-finding-* que
viven en frontend/src/theme/tokens.css con los mismos valores.
"""

FINDING_CATALOG: dict[str, dict[str, str]] = {
    "sano": {"label": "Sano", "color": "#A9C6B8", "symbol": ""},
    "caries": {"label": "Caries", "color": "#D64545", "symbol": "C"},
    "restauracion": {"label": "Restauracion", "color": "#4A90C2", "symbol": "R"},
    "corona": {"label": "Corona", "color": "#E0A100", "symbol": "CO"},
    "endodoncia": {"label": "Endodoncia", "color": "#7B5EA7", "symbol": "E"},
    # Negro (antes gris #8C8C8C): leyenda oficial de docs/clinica, "Negro: Dientes
    # ausentes o restos radiculares". Ver nota equivalente en theme/tokens.css.
    "ausente": {"label": "Ausente", "color": "#1A1A1A", "symbol": "X"},
    "extraccion_indicada": {"label": "Extraccion indicada", "color": "#D64545", "symbol": "XI"},
    "implante": {"label": "Implante", "color": "#2BB3A3", "symbol": "IM"},
    "protesis_fija": {"label": "Protesis fija", "color": "#3A7FC1", "symbol": "PF"},
    # Reasignado de verde (ahora de "biopelicula_tartaro") a este magenta, para no chocar
    # con la leyenda oficial de 4 colores.
    "sellador": {"label": "Sellador", "color": "#A8407D", "symbol": "S"},
    "fractura": {"label": "Fractura", "color": "#B8460E", "symbol": "FX"},
    "movilidad": {"label": "Movilidad", "color": "#C77D1E", "symbol": "MO"},
    # Hallazgo nuevo (leyenda oficial de docs/clinica, "Verde: biopelicula y tartaro
    # dental"): reusa el verde que antes tenia "sellador".
    "biopelicula_tartaro": {
        "label": "Biopelicula y tartaro dental",
        "color": "#6AB04C",
        "symbol": "BT",
    },
}

FINDING_CODES: tuple[str, ...] = tuple(FINDING_CATALOG.keys())
