"""Catalogo de diagnosticos, aislado de la BD.

Catalogo configurable (CLAUDE.md sec. 7): valores por defecto razonables, a validar
con la clinica (ver docs/PENDIENTES_CLINICOS.md). El texto de cada Diagnosis siempre
es libre; este catalogo solo ofrece codigo + etiqueta para un selector rapido en la
UI -- no es obligatorio partir de el.
"""

DIAGNOSIS_CATALOG: dict[str, str] = {
    "caries": "Caries dental",
    "caries_recurrente": "Caries recurrente",
    "pulpitis_reversible": "Pulpitis reversible",
    "pulpitis_irreversible": "Pulpitis irreversible",
    "necrosis_pulpar": "Necrosis pulpar",
    "absceso_periapical": "Absceso periapical",
    "gingivitis": "Gingivitis",
    "periodontitis": "Periodontitis",
    "fractura_dental": "Fractura dental",
    "edentulismo_parcial": "Edentulismo parcial",
    "maloclusion": "Maloclusion",
    "sin_hallazgos": "Sin hallazgos patologicos",
}
DIAGNOSIS_CODES: tuple[str, ...] = tuple(DIAGNOSIS_CATALOG.keys())
