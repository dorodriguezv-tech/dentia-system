"""Reglas y catalogos de la Historia Clinica de Endodoncia (Fase F del
rediseno del expediente, docs/clinica), aisladas de la BD.

A diferencia de las Fases C/E, NINGUN checklist de esta fase usa catalogo
administrable (app.modules.catalogs): la especificacion los describe como
checklists cerrados y pequenos, igual criterio que
`odontological_history.rules.RADIOGRAPHIC_FINDING_TYPES`. Se validan aqui
contra tuplas fijas, directamente en `service.py` (sin tocar la BD de
catalogos).
"""

from app.modules.odontogram.rules import TOOTH_FDI_PERMANENT

ORIGINS: tuple[str, ...] = ("MANUAL", "AI_ASSISTED")

# --------------------------------------------------------------------------------
# 1. Interrogatorio (Antecedentes / Dolor / Estimulo) + Examen Intrabucal +
# Examen Extrabucal.
# --------------------------------------------------------------------------------

ANTECEDENTES_KEYS: tuple[str, ...] = (
    "caries",
    "traumatismo",
    "abrasion",
    "resina",
    "amalgama",
    "incrustacion",
    "corona_poste",
    "tratamiento_conductos",
    "otros",
)
DOLOR_KEYS: tuple[str, ...] = ("localizado", "irradiado", "espontaneo", "provocado", "otro")
ESTIMULO_KEYS: tuple[str, ...] = ("frio", "calor", "masticacion", "dulce", "otro")
EXAMEN_INTRABUCAL_KEYS: tuple[str, ...] = (
    "exposicion_pulpar",
    "inflamacion",
    "fistula",
    "traumatismo",
    "lesion_tejidos_blandos",
    "otro",
)
EXAMEN_EXTRABUCAL_KEYS: tuple[str, ...] = (
    "inflamacion",
    "fistula",
    "ganglios_linfaticos",
    "otro",
)

# --------------------------------------------------------------------------------
# 3. Pruebas periodontales. Percusion horizontal y vertical comparten el mismo
# conjunto de claves (son 2 columnas del mismo formulario, no catalogos
# distintos).
# --------------------------------------------------------------------------------

PERCUSION_KEYS: tuple[str, ...] = ("fugaz", "persistente", "localizado", "irradiado")
MOVILIDAD_VALUES: tuple[str, ...] = ("positiva", "negativa")
MOVILIDAD_GRADOS: tuple[str, ...] = ("I", "II", "III")
PALPACION_VALUES: tuple[str, ...] = ("positiva", "negativa")

# --------------------------------------------------------------------------------
# 4. Interpretacion radiografica.
# --------------------------------------------------------------------------------

CAMARA_KEYS: tuple[str, ...] = (
    "normal",
    "estrecha",
    "calcificada",
    "fractura",
    "perforacion",
    "retraccion",
    "obstruccion",
    "otro",
)
CONDUCTO_KEYS: tuple[str, ...] = (
    "normal_estrecho",
    "amplio_preparado",
    "obturado",
    "inmaduro",
    "resorcion_interna",
    "perforado",
    "calcificado",
    "fractura",
    "otro",
)
PERIODONTO_KEYS: tuple[str, ...] = (
    "normal_ensanchado",
    "resorcion_apical",
    "hipercementosis",
    "lesion_difusa",
    "lesion_circunscrita",
    "otro",
)

# --------------------------------------------------------------------------------
# 5. Diagnostico y tratamiento: diagnosticos pulpar/periapical son seleccion
# UNICA (catalogo cerrado -- clinicamente es un diagnostico, no multi-select);
# tratamiento/cirugia son multi-select (checklist).
# --------------------------------------------------------------------------------

DIAGNOSTICO_PULPAR_VALUES: tuple[str, ...] = (
    "pulpa_sana",
    "pulpitis_reversible",
    "pulpitis_irreversible",
    "necrosis_pulpar",
    "despulpado",
    "pulpitis_hiperplasica",
)
DIAGNOSTICO_PERIAPICAL_VALUES: tuple[str, ...] = (
    "periapice_sano",
    "periodontitis_aguda",
    "periodontitis_cronica",
    "osteitis_condensante",
    "absceso_alveolar_agudo",
    "absceso_fenix_cronico",
)
TRATAMIENTO_KEYS: tuple[str, ...] = (
    "biopulpectomia",
    "necropulpectomia",
    "repeticion_tratamiento",
    "extirpacion_intencional",
    "apicoformacion",
    "recromia",
    "perno_munon",
)
CIRUGIA_KEYS: tuple[str, ...] = (
    "curetaje_apical",
    "apicectomia",
    "radisectomia",
    "hemiseccion",
    "amputacion_radicular",
)

# --------------------------------------------------------------------------------
# 6. Odontograma de diagnostico y de evolucion: 18 codigos numericos (0-17)
# propios de endodoncia, independientes del catalogo general del odontograma
# (Fase B, `app.modules.odontogram`) -- NO se toca ese catalogo. Solo piezas
# FDI permanentes (el dibujo del PDF original no incluye temporales), se
# reutiliza `TOOTH_FDI_PERMANENT` de `app.modules.odontogram.rules` en vez de
# duplicarlo.
# --------------------------------------------------------------------------------

ENDODONTIC_TOOTH_CODES: tuple[tuple[int, str], ...] = (
    (0, "sano"),
    (1, "con_caries"),
    (2, "obturado_con_caries"),
    (3, "obturado_sin_caries"),
    (4, "perdido_por_caries"),
    (5, "perdido_otro_motivo"),
    (6, "fisura_obturada"),
    (7, "soporte_puente_corona_funda_implante"),
    (8, "diente_sin_erupcionar"),
    (9, "traumatismo_fractura"),
    (10, "no_registrado"),
    (11, "recesion_gingival"),
    (12, "tratamiento_conductos"),
    (13, "instrumento_separado_conducto"),
    (14, "bolsas_periodontales"),
    (15, "fluorosis"),
    (16, "alteraciones_forma_numero_tamano_textura_posicion"),
    (17, "lesion_endoperiodontal"),
)
ENDODONTIC_TOOTH_CODE_VALUES: frozenset[int] = frozenset(code for code, _ in ENDODONTIC_TOOTH_CODES)
ENDODONTIC_TOOTH_CODE_LABELS: dict[int, str] = dict(ENDODONTIC_TOOTH_CODES)

ENDODONTIC_TOOTH_KINDS: tuple[str, ...] = ("diagnostico", "evolucion")

TOOTH_FDI_PERMANENT_CODES: frozenset[str] = frozenset(str(t) for t in TOOTH_FDI_PERMANENT)


def is_valid_permanent_tooth_code(tooth_fdi: str) -> bool:
    return tooth_fdi in TOOTH_FDI_PERMANENT_CODES


def is_valid_endodontic_tooth_code(code: int) -> bool:
    return code in ENDODONTIC_TOOTH_CODE_VALUES


# --------------------------------------------------------------------------------
# 7. Longitud de trabajo: claves validas de `canal_measurements`.
# --------------------------------------------------------------------------------

CANAL_KEYS: tuple[str, ...] = (
    "mesial",
    "mesiolingual",
    "mesiovestibular",
    "mesiopalatino",
    "distal",
    "distolingual",
    "distopalatino",
    "distovestibular",
    "palatino",
    "unico",
)
