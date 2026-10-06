"""Contraste WCAG y derivacion de color (docs/04_TEMAS_Y_MARCA.md sec. 4)."""

import colorsys
import re

HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")

RGB = tuple[float, float, float]


def is_valid_hex(value: str) -> bool:
    return bool(HEX_PATTERN.match(value))


def hex_to_rgb(hex_color: str) -> RGB:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(rgb: RGB) -> str:
    clamped = (max(0, min(255, round(c))) for c in rgb)
    return "#{:02X}{:02X}{:02X}".format(*clamped)


def _linearize(channel: float) -> float:
    c = channel / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(rgb: RGB) -> float:
    r, g, b = (_linearize(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(hex_a: str, hex_b: str) -> float:
    la = relative_luminance(hex_to_rgb(hex_a))
    lb = relative_luminance(hex_to_rgb(hex_b))
    lighter, darker = max(la, lb), min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def adjust_lightness(hex_color: str, delta: float) -> str:
    r, g, b = (c / 255 for c in hex_to_rgb(hex_color))
    h, lightness, s = colorsys.rgb_to_hls(r, g, b)
    lightness = max(0.0, min(1.0, lightness + delta))
    r2, g2, b2 = colorsys.hls_to_rgb(h, lightness, s)
    return rgb_to_hex((r2 * 255, g2 * 255, b2 * 255))


def derive_hover(primary_hex: str) -> str:
    """--color-primary-hover: ~12% mas oscuro."""
    return adjust_lightness(primary_hex, -0.12)


def derive_soft(primary_hex: str) -> str:
    """--color-primary-soft: aclarado hacia blanco, para fondos suaves.

    0.65, no 0.38 (valor original): varios componentes (p.ej. la insignia de
    estado del paciente) usan el primario mismo como color de TEXTO sobre este
    fondo -- con 0.38 el fondo quedaba demasiado cerca del primario y ese par
    nunca llegaba a 4.5:1 sin importar que tan oscuro fuera el primario (bug
    real encontrado en la Fase 12 con una auditoria automatica, axe-core).
    0.65 deja margen (~4.6:1) para cualquier primario que ya pase su propio
    chequeo de contraste contra blanco."""
    return adjust_lightness(primary_hex, 0.65)


def suggest_contrasting_color(fg_hex: str, bg_hex: str, target: float = 4.5) -> str:
    """Oscurece o aclara fg_hex hasta alcanzar el contraste objetivo contra bg_hex."""
    if contrast_ratio(fg_hex, bg_hex) >= target:
        return fg_hex

    bg_is_light = relative_luminance(hex_to_rgb(bg_hex)) > 0.5
    direction = -1 if bg_is_light else 1

    candidate = fg_hex
    for step in range(1, 26):
        candidate = adjust_lightness(fg_hex, direction * step * 0.04)
        if contrast_ratio(candidate, bg_hex) >= target:
            return candidate
    return candidate
