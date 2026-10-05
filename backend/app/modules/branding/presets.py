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
        "primary": "#2BB3A3",
        "secondary": "#4A90C2",
        "accent": "#F2A65A",
        "bg": "#F7FAFA",
    },
    "azul_sereno": {
        "name": "Azul sereno",
        "primary": "#3A7FC1",
        "secondary": "#5BBFD6",
        "accent": "#F4B860",
        "bg": "#F5F8FC",
    },
    "aqua_suave": {
        "name": "Aqua suave",
        "primary": "#1FA2B8",
        "secondary": "#7CC6A6",
        "accent": "#FF9F80",
        "bg": "#F4FAFB",
    },
    "lavanda_suave": {
        "name": "Lavanda suave",
        "primary": "#7B7FD4",
        "secondary": "#5FB3C9",
        "accent": "#F2B5A0",
        "bg": "#F8F8FD",
    },
    "verde_salvia": {
        "name": "Verde salvia",
        "primary": "#6A9E7F",
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
