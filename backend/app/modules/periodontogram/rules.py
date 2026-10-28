"""Reglas y catalogos del Periodontograma completo (Fase G del rediseno del
expediente, docs/clinica -- ULTIMO slice del proyecto), aisladas de la BD.

Ningun valor de este modulo es catalogo administrable
(`app.modules.catalogs`): todos son enteros/enums fijos y pequenos (CLAUDE.md
sec. 7: "si una decision clinica no esta definida, usa un catalogo
configurable con valores por defecto razonables" -- aqui no aplica un
catalogo EDITABLE porque son escalas clinicas estandar universales, no listas
que una clinica mexicana concreta vaya a querer personalizar, a diferencia de
`skull_type`/`pediatric_character`/etc. de fases previas). Ver nota de
ambiguedad del PDF original y la decision de diseno en
docs/PENDIENTES_CLINICOS.md.
"""

from app.modules.odontogram.rules import TOOTH_FDI_PERMANENT

ORIGINS: tuple[str, ...] = ("MANUAL", "AI_ASSISTED")

# --------------------------------------------------------------------------------
# 1. Sondeo periodontal -- 6 sitios estandar por pieza. "lingual" aplica
# igual para la arcada superior, donde clinicamente es "palatino" -- es solo
# una etiqueta de interfaz (PROBING_SITE_LABELS), el codigo no distingue
# arcada.
# --------------------------------------------------------------------------------

PROBING_SITES: tuple[str, ...] = (
    "mesiovestibular",
    "vestibular",
    "distovestibular",
    "mesiolingual",
    "lingual",
    "distolingual",
)

PROBING_SITE_LABELS: dict[str, str] = {
    "mesiovestibular": "Mesiovestibular",
    "vestibular": "Vestibular",
    "distovestibular": "Distovestibular",
    "mesiolingual": "Mesiolingual/Mesiopalatino",
    "lingual": "Lingual/Palatino",
    "distolingual": "Distolingual/Distopalatino",
}

PROBING_DEPTH_MM_MIN = 0
PROBING_DEPTH_MM_MAX = 15
# La recesion puede ser negativa: agrandamiento/cobertura gingival sobre la
# union cemento-esmalte (caso raro pero valido clinicamente).
RECESSION_MM_MIN = -5
RECESSION_MM_MAX = 15

# --------------------------------------------------------------------------------
# 2. Medicion por pieza -- movilidad (clasificacion de Miller) y furcacion.
# --------------------------------------------------------------------------------

MOBILITY_GRADE_MIN = 0
MOBILITY_GRADE_MAX = 3
FURCATION_GRADE_MIN = 0
FURCATION_GRADE_MAX = 3

# --------------------------------------------------------------------------------
# 3. Indices de placa dentobacteriana y gingival -- 2 superficies por pieza
# (NO 6 sitios: el PDF muestra una cuadricula mas simple para los indices que
# para el sondeo). "lingual" = lingual/palatino segun arcada, igual criterio
# de etiqueta de interfaz que el sondeo.
# --------------------------------------------------------------------------------

INDEX_TYPES: tuple[str, ...] = ("placa", "gingival")
INDEX_SURFACES: tuple[str, ...] = ("vestibular", "lingual")
INDEX_SURFACE_LABELS: dict[str, str] = {
    "vestibular": "Vestibular",
    "lingual": "Lingual/Palatino",
}
INDEX_GRADE_MIN = 0
INDEX_GRADE_MAX = 3

PLAQUE_GRADE_LABELS: dict[int, str] = {
    0: "Ausencia de placa",
    1: "Placa en 1/3 de la superficie",
    2: "Placa en 2/3 de la superficie",
    3: "Placa en mas de 2/3 de la superficie",
}

GINGIVAL_GRADE_LABELS: dict[int, str] = {
    0: "Normal (encia sana)",
    1: "Leve (cambio de color/edema leve, sin sangrado al sondaje)",
    2: "Moderada (enrojecimiento evidente, sangrado al sondaje)",
    3: "Severa (enrojecimiento/edema severo, ulceracion, tendencia a sangrado espontaneo)",
}

# --------------------------------------------------------------------------------
# 4. Tablas de oclusion -- 4 movimientos.
# --------------------------------------------------------------------------------

OCCLUSAL_MOVEMENTS: tuple[str, ...] = (
    "centrica",
    "lateralidad_izquierda",
    "protrusion",
    "lateralidad_derecha",
)

OCCLUSAL_MOVEMENT_LABELS: dict[str, str] = {
    "centrica": "Oclusion centrica",
    "lateralidad_izquierda": "Lateralidad izquierda",
    "protrusion": "Protrusion",
    "lateralidad_derecha": "Lateralidad derecha",
}

# --------------------------------------------------------------------------------
# Piezas validas: solo permanentes (el dibujo del PDF original no muestra
# temporales, a diferencia del odontograma pediatrico de la Fase E) --
# reutiliza TOOTH_FDI_PERMANENT de app.modules.odontogram.rules, no se
# duplica.
# --------------------------------------------------------------------------------

TOOTH_FDI_PERMANENT_CODES: frozenset[str] = frozenset(str(t) for t in TOOTH_FDI_PERMANENT)


def is_valid_permanent_tooth_code(tooth_fdi: str) -> bool:
    return tooth_fdi in TOOTH_FDI_PERMANENT_CODES


# --------------------------------------------------------------------------------
# Calculos derivados -- NINGUNO se persiste (mismo criterio que el IMC de la
# Fase A, `records/rules.py::body_mass_index`): se calculan al vuelo para que
# el dato nunca quede desincronizado de sus componentes.
# --------------------------------------------------------------------------------


def clinical_attachment_level_mm(probing_depth_mm: int, recession_mm: int) -> int:
    """Nivel de inserccion clinica (CAL) = profundidad de sondaje +
    recesion."""
    return probing_depth_mm + recession_mm


def compute_plaque_index(grades: list[int]) -> tuple[int, int, float | None]:
    """Indice de placa dentobacteriana (criterio O'Leary): proporcion de
    caras con placa visible (`grade > 0`) sobre el total de caras
    registradas para `index_type="placa"`. Devuelve
    (numero_caras_totales, numero_caras_pigmentadas, indice) -- `indice` es
    `None` si no hay caras registradas (division por cero evitada a
    proposito, no es 0.0)."""
    total = len(grades)
    pigmented = sum(1 for grade in grades if grade > 0)
    if total == 0:
        return 0, 0, None
    return total, pigmented, round(pigmented / total, 4)


def compute_gingival_index(grades: list[int]) -> tuple[int, float | None]:
    """Indice gingival total (criterio de Loe-Silness): media aritmetica de
    los grados registrados para `index_type="gingival"`. Devuelve
    (numero_sitios_totales, indice) -- `indice` es `None` si no hay sitios
    registrados."""
    total = len(grades)
    if total == 0:
        return 0, None
    return total, round(sum(grades) / total, 4)
