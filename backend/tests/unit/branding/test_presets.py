import pytest

from app.modules.branding import color_utils
from app.modules.branding.presets import PRESETS

WCAG_AA_MINIMUM = 4.5


@pytest.mark.parametrize("code", list(PRESETS.keys()))
def test_every_preset_primary_passes_wcag_aa_against_white_and_its_own_bg(
    code: str,
) -> None:
    """Regresion de accessibility.spec.ts (axe-core): "azul_sereno", "aqua_suave",
    "lavanda_suave" y "verde_salvia" se quedaron con el mismo bug que ya se habia
    corregido en "menta_clinica" (Fase 12) -- un primario que no llega a 4.5:1 como
    texto sobre blanco/--color-bg ni como fondo de boton con texto blanco. Esta
    prueba cubre los 6 presets, no solo los que ya fallaron una vez, para que un
    preset nuevo con el mismo defecto no pase desapercibido otra vez."""
    primary = PRESETS[code]["primary"]
    bg = PRESETS[code]["bg"]

    assert color_utils.contrast_ratio(primary, "#FFFFFF") >= WCAG_AA_MINIMUM
    assert color_utils.contrast_ratio(primary, bg) >= WCAG_AA_MINIMUM
