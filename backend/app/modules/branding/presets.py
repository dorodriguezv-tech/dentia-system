"""Catalogo de presets y paleta por defecto (docs/04_TEMAS_Y_MARCA.md sec. 2 y 3).

Fuente de verdad unica: frontend/src/theme/presets.ts es una copia para la UI
(selector de presets), igual que el catalogo de permisos de IAM.
"""

DEFAULT_PRESET = "menta_clinica"

# Colores comunes a todos los presets: el preset solo cambia primary/secondary/accent/bg
# (ver la tabla de docs/04, que no varia el resto). Los semanticos (success/warning/danger)
# se mantienen fijos para que signifiquen siempre lo mismo sin importar la marca.
_SHARED_DEFAULTS = {
    "surface": "#FFFFFF",
    "border": "#DCE6E5",
    "text": "#1F2D2B",
    "text_muted": "#5E6E6C",
    "success": "#3BA55C",
    "warning": "#E0A100",
    "danger": "#D64545",
}

PRESETS: dict[str, dict[str, str]] = {
    "menta_clinica": {
        "name": "Menta clinica",
        # #2BB3A3 (el teal original) no pasa el propio chequeo de contraste WCAG de
        # este modulo (sec. 4 de docs/04_TEMAS_Y_MARCA.md, 4.5:1): como texto sobre
        # blanco/bg daba ~2.5:1, y texto blanco sobre el boton primario tambien
        # ~2.6:1. Bug real encontrado en la Fase 12 con una auditoria automatica
        # (axe-core) -- #1E7D72 es el mismo tono oscurecido (con margen, >=4.7:1
        # contra blanco y contra --color-bg) con la misma logica de
        # color_utils.suggest_contrasting_color(). Los demas presets no se
        # tocaron: un preset que un usuario elige y guarda ya pasa por ese mismo
        # validador en tiempo de ejecucion (avisa y sugiere un ajuste); el preset
        # por defecto es el unico que nunca pasaba por ahi.
        "primary": "#1E7D72",
        "secondary": "#4A90C2",
        "accent": "#F2A65A",
        "bg": "#F7FAFA",
    },
    "azul_sereno": {
        "name": "Azul sereno",
        # #3A7FC1 (el azul original) no pasaba el contraste WCAG 4.5:1 (sec. 4 de
        # docs/04_TEMAS_Y_MARCA.md): 4.21:1 contra blanco/bg y contra texto blanco
        # sobre el boton primario -- la misma clase de bug que menta_clinica (Fase 12),
        # encontrada aqui hasta que una sucursal real eligio este preset y
        # accessibility.spec.ts (axe-core) la agarro. #3575B1 es el mismo tono
        # oscurecido con color_utils.suggest_contrasting_color(), >=4.5:1 contra
        # blanco y contra --color-bg.
        "primary": "#3575B1",
        "secondary": "#5BBFD6",
        "accent": "#F4B860",
        "bg": "#F5F8FC",
    },
    "aqua_suave": {
        "name": "Aqua suave",
        # Mismo bug y misma correccion que azul_sereno (ver arriba): #1FA2B8 original
        # daba ~3.0:1, #167484 pasa >=4.5:1.
        "primary": "#167484",
        "secondary": "#7CC6A6",
        "accent": "#FF9F80",
        "bg": "#F4FAFB",
    },
    "lavanda_suave": {
        "name": "Lavanda suave",
        # Mismo bug y misma correccion que azul_sereno (ver arriba): #7B7FD4 original
        # daba ~3.6:1, #5C61CA pasa >=4.5:1.
        "primary": "#5C61CA",
        "secondary": "#5FB3C9",
        "accent": "#F2B5A0",
        "bg": "#F8F8FD",
    },
    "verde_salvia": {
        "name": "Verde salvia",
        # Mismo bug y misma correccion que azul_sereno (ver arriba): #6A9E7F original
        # daba ~3.1:1, #507B61 pasa >=4.5:1.
        "primary": "#507B61",
        "secondary": "#4F8FA8",
        "accent": "#E8B04B",
        "bg": "#F6F9F6",
    },
    "grafito_profesional": {
        "name": "Grafito profesional",
        "primary": "#37515F",
        "secondary": "#2BB3A3",
        "accent": "#F2A65A",
        "bg": "#F6F7F8",
    },
}

COLOR_KEYS = (
    "primary",
    "secondary",
    "accent",
    "bg",
    "surface",
    "border",
    "text",
    "text_muted",
    "success",
    "warning",
    "danger",
)


def full_palette(preset_code: str) -> dict[str, str]:
    preset = PRESETS[preset_code]
    return {
        "primary": preset["primary"],
        "secondary": preset["secondary"],
        "accent": preset["accent"],
        "bg": preset["bg"],
        **_SHARED_DEFAULTS,
    }
