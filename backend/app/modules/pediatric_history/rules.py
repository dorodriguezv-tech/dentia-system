"""Reglas y catalogos de la Historia Clinica Pediatrica (Fase E del rediseno
del expediente, docs/clinica), aisladas de la BD. Mismo criterio que
`odontological_history/rules.py` (Fase C): catalogos configurables (CLAUDE.md
sec. 7), valores por defecto razonables, a validar con la clinica real (ver
docs/PENDIENTES_CLINICOS.md).

Nota importante (corrige una nota del plan original): la distincion
congenito/adquirida de una pieza ausente NO se modela como codigo nuevo del
catalogo GLOBAL `odontogram_finding` (eso rompería la leyenda de 4 colores ya
cerrada de Historia General/Odontologica/Tratamiento, Fase B). Aqui se modela
como dos valores mas del catalogo `pediatric_tooth_anomaly`, exclusivo de esta
historia -- ver `PediatricToothAnnotation` en models.py.
"""

from app.modules.odontogram.rules import TOOTH_FDI_ALL

ORIGINS: tuple[str, ...] = ("MANUAL", "AI_ASSISTED")

# --------------------------------------------------------------------------------
# 3. Madurez y conducta -- catalogo administrable "pediatric_character".
# --------------------------------------------------------------------------------

PEDIATRIC_CHARACTER_OPTIONS: tuple[str, ...] = (
    "apatico",
    "introvertido_moderado",
    "inquieto",
    "irritable",
    "hiperactivo",
    "agresivo",
)

# --------------------------------------------------------------------------------
# 4. Oclusion y alineamiento -- catalogo administrable "terminal_plane" y
# Literal fijos para linea media / clasificacion de Angle (el PDF los da como
# opciones cerradas explicitas, no listas largas que valga la pena administrar).
# --------------------------------------------------------------------------------

TERMINAL_PLANE_OPTIONS: tuple[str, ...] = ("recto", "mesial", "distal")
LINEA_MEDIA_OPTIONS: tuple[str, ...] = ("normal", "desviada_izquierda", "desviada_derecha")
CLASIFICACION_ANGLE_OPTIONS: tuple[str, ...] = ("I", "II", "III")

# --------------------------------------------------------------------------------
# 6. Odontograma pediatrico -- anotaciones: catalogo administrable
# "pediatric_tooth_anomaly". `ausente_congenito`/`ausente_adquirida` son los dos
# que el frontend dibuja como triangulo amarillo/verde respectivamente (ver nota
# de correccion arriba) -- NO tocan el catalogo global `odontogram_finding`.
# --------------------------------------------------------------------------------

PEDIATRIC_TOOTH_ANOMALY_OPTIONS: tuple[tuple[str, str], ...] = (
    ("diente_fusionado", "Diente fusionado (fu)"),
    ("geminacion_dentinaria", "Geminacion dentinaria (Gem)"),
    ("diente_supernumerario", "Diente supernumerario (Sn)"),
    ("hipoplasia", "Hipoplasia (Hip)"),
    ("diente_traumatizado", "Diente traumatizado (tr)"),
    ("cerca_exfoliacion", "Cerca de exfoliacion (CEx)"),
    ("movilidad", "Movilidad en el diente (MV)"),
    ("inflamacion_gingival", "Inflamacion Gingival (PMA)"),
    ("ausente_congenito", "Ausente (congenito)"),
    ("ausente_adquirida", "Ausente por extraccion o exfoliacion"),
)
PEDIATRIC_TOOTH_ANOMALY_CODES: frozenset[str] = frozenset(
    code for code, _ in PEDIATRIC_TOOTH_ANOMALY_OPTIONS
)

# Piezas validas para el odontograma pediatrico: permanentes Y temporales (a
# diferencia del diagnostico/plan de Fase C que solo admitia permanentes) --
# reutiliza TOOTH_FDI_ALL de app.modules.odontogram.rules, no se duplica.
TOOTH_FDI_ALL_CODES: frozenset[str] = frozenset(str(t) for t in TOOTH_FDI_ALL)


def is_valid_tooth_code(tooth_fdi: str) -> bool:
    return tooth_fdi in TOOTH_FDI_ALL_CODES


# --------------------------------------------------------------------------------
# 5. Erupcion y denticion -- tabla de referencia ESTATICA de cronologia de
# erupcion/caida (incisivo central 8-12 meses erupcion / 6-7 anos se cae, etc.),
# tal como aparece en el PDF original. NO es una estructura de BD (nada se
# captura aqui): es contenido fijo de consulta para que el frontend lo muestre
# como tabla de referencia junto al formulario de esta seccion. Valores segun
# la cronologia estandar de denticion (American Dental Association / literatura
# de odontopediatria clasica), no especificos de esta clinica.
# --------------------------------------------------------------------------------

PRIMARY_TOOTH_ERUPTION_CHRONOLOGY: tuple[dict[str, str], ...] = (
    {
        "diente": "Incisivo central",
        "erupcion": "6-10 meses (inferior), 8-12 meses (superior)",
        "caida": "6-7 anos",
    },
    {
        "diente": "Incisivo lateral",
        "erupcion": "10-16 meses (inferior), 9-13 meses (superior)",
        "caida": "7-8 anos",
    },
    {
        "diente": "Canino",
        "erupcion": "17-23 meses",
        "caida": "10-12 anos",
    },
    {
        "diente": "Primer molar",
        "erupcion": "14-18 meses (inferior), 13-19 meses (superior)",
        "caida": "9-11 anos",
    },
    {
        "diente": "Segundo molar",
        "erupcion": "23-31 meses (inferior), 25-33 meses (superior)",
        "caida": "10-12 anos",
    },
)

PERMANENT_TOOTH_ERUPTION_CHRONOLOGY: tuple[dict[str, str], ...] = (
    {"diente": "Incisivo central", "erupcion": "6-8 anos"},
    {"diente": "Incisivo lateral", "erupcion": "7-9 anos"},
    {"diente": "Canino", "erupcion": "9-12 anos"},
    {"diente": "Primer premolar", "erupcion": "10-12 anos"},
    {"diente": "Segundo premolar", "erupcion": "10-12 anos"},
    {"diente": "Primer molar", "erupcion": "6-7 anos"},
    {"diente": "Segundo molar", "erupcion": "11-13 anos"},
    {"diente": "Tercer molar", "erupcion": "17-21 anos"},
)
