from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from app.modules.branding.color_utils import is_valid_hex
from app.modules.branding.presets import COLOR_KEYS

PresetCode = Literal[
    "dentia",
    "menta_clinica",
    "azul_sereno",
    "aqua_suave",
    "lavanda_suave",
    "verde_salvia",
    "grafito_profesional",
    "custom",
]

RadiusCode = Literal["soft", "sharp"]


class ColorPalette(BaseModel):
    primary: str
    secondary: str
    accent: str
    bg: str
    surface: str
    border: str
    text: str
    text_muted: str
    success: str
    warning: str
    danger: str

    @field_validator(*COLOR_KEYS)
    @classmethod
    def _validate_hex(cls, value: str) -> str:
        if not is_valid_hex(value):
            raise ValueError(f"Color invalido: {value!r} (se espera #RRGGBB)")
        return value.upper()


class PresetOut(BaseModel):
    code: str
    name: str
    primary: str
    secondary: str
    accent: str
    bg: str


class ContrastWarning(BaseModel):
    pair: str
    ratio: float
    suggested_color: str


class BrandingOut(BaseModel):
    display_name: str
    subtitle: str | None
    preset: str
    colors: ColorPalette
    dark_mode: bool
    radius: RadiusCode
    logo_url: str | None
    favicon_url: str | None
    # W2 (docs/CAMBIOS_WEB_MARCA.md): logo_url/favicon_url ahora siempre traen algo
    # que mostrar (el propio o el de DENT-IA por defecto); este campo es la unica
    # forma de saber si es el logo propio de la sucursal, para mostrar o no
    # "con tecnologia DENT-IA" debajo.
    has_custom_logo: bool
    contrast_warnings: list[ContrastWarning] = Field(default_factory=list)


class BrandingUpdateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=200)
    subtitle: str | None = Field(default=None, max_length=300)
    preset: PresetCode
    colors: ColorPalette | None = None
    dark_mode: bool = False
    radius: RadiusCode = "soft"

    @model_validator(mode="after")
    def _require_colors_when_custom(self) -> Self:
        if self.preset == "custom" and self.colors is None:
            raise ValueError("colors es obligatorio cuando preset='custom'")
        return self
