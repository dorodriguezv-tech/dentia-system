"""Catalogos y reglas del odontograma (regla 5 de CLAUDE.md), aisladas de la BD.

Catalogos configurables (CLAUDE.md sec. 7): valores por defecto razonables, a validar
con la clinica (ver docs/PENDIENTES_CLINICOS.md).
"""

TOOTH_FDI_PERMANENT: tuple[int, ...] = tuple(
    quadrant * 10 + position for quadrant in (1, 2, 3, 4) for position in range(1, 9)
)
TOOTH_FDI_TEMPORARY: tuple[int, ...] = tuple(
    quadrant * 10 + position for quadrant in (5, 6, 7, 8) for position in range(1, 6)
)
TOOTH_FDI_ALL: frozenset[int] = frozenset(TOOTH_FDI_PERMANENT) | frozenset(TOOTH_FDI_TEMPORARY)

SURFACES: tuple[str, ...] = ("O", "M", "D", "V", "L", "P", "I")
KINDS: tuple[str, ...] = ("EXISTING", "PLANNED", "PERFORMED")
ORIGINS: tuple[str, ...] = ("MANUAL", "AI_ASSISTED")

_UPPER_QUADRANTS = {1, 2, 5, 6}
# Anteriores = incisivos (posicion 1, 2) y canino (posicion 3): se les asigna superficie
# incisal en vez de oclusal. Ver pendiente clinico sobre si el canino debe tratarse como
# anterior (incisal) o posterior (oclusal) en docs/PENDIENTES_CLINICOS.md.
_ANTERIOR_POSITIONS = {1, 2, 3}


def is_valid_tooth(tooth_fdi: int) -> bool:
    return tooth_fdi in TOOTH_FDI_ALL


def is_temporary_tooth(tooth_fdi: int) -> bool:
    return tooth_fdi in TOOTH_FDI_TEMPORARY


def is_upper_tooth(tooth_fdi: int) -> bool:
    return (tooth_fdi // 10) in _UPPER_QUADRANTS


def is_anterior_tooth(tooth_fdi: int) -> bool:
    return (tooth_fdi % 10) in _ANTERIOR_POSITIONS


def valid_surfaces_for_tooth(tooth_fdi: int) -> frozenset[str]:
    """Las 5 superficies clicables de una pieza: P solo en piezas superiores, L en
    inferiores; I solo en anteriores (incisivos/canino), O en posteriores."""
    surfaces = {"M", "D", "V"}
    surfaces.add("P" if is_upper_tooth(tooth_fdi) else "L")
    surfaces.add("I" if is_anterior_tooth(tooth_fdi) else "O")
    return frozenset(surfaces)


def is_valid_surface_for_tooth(tooth_fdi: int, surface: str | None) -> bool:
    if surface is None:
        return True  # hallazgo de toda la pieza (p.ej. ausente, implante, corona)
    return surface in valid_surfaces_for_tooth(tooth_fdi)
