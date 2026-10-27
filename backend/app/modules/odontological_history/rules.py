"""Reglas y catalogos de la Historia Clinica Odontologica (Fase C, aisladas de
la BD). Catalogos configurables (CLAUDE.md sec. 7): valores por defecto
razonables, a validar con la clinica (ver docs/PENDIENTES_CLINICOS.md).
"""

from app.modules.odontogram.rules import TOOTH_FDI_ALL, TOOTH_FDI_PERMANENT

ORIGINS: tuple[str, ...] = ("MANUAL", "AI_ASSISTED")

# --------------------------------------------------------------------------------
# 1. Exploracion cabeza/cuello + biotipo facial + ATM + tejidos blandos.
# --------------------------------------------------------------------------------

SKULL_TYPES: tuple[str, ...] = ("mesocefalo", "braquicefalo", "dolicocefalo")
FACIAL_BIOTYPES: tuple[str, ...] = ("mesofacial", "braquifacial", "dolicofacial")

# --------------------------------------------------------------------------------
# 2. Anamnesis periodontal (cuestionario de entrevista, NO sondeo clinico -- el
# periodontograma completo con sondeo de 6 sitios/diente e indices de placa/
# gingival calculados por cara queda para la Fase G, ver
# docs/PENDIENTES_CLINICOS.md).
#
# Nota de discrepancia con la especificacion: el encargo describe "32
# preguntas" pero enumera explicitamente solo 30 codigos (la pregunta 1 del
# PDF original se reparte en 3 sub-respuestas: sensibilidad_frio/calor/
# masticar, por eso el PDF de 28 preguntas rinde 30 codigos aqui). Se siguio
# la lista literal de codigos (fuente de verdad explicita), documentado
# tambien en docs/PENDIENTES_CLINICOS.md para validar con la clinica real.
# --------------------------------------------------------------------------------

PERIODONTAL_ANAMNESIS_ANSWER_VALUES: tuple[str, ...] = ("si", "no", "no_recuerda")

# (codigo, texto completo de la pregunta) -- orden y texto tal como los dio la
# especificacion; se usa para sembrar el catalogo "periodontal_anamnesis_question"
# (app.modules.catalogs) y como `name` legible en el PDF.
PERIODONTAL_ANAMNESIS_QUESTIONS: tuple[tuple[str, str], ...] = (
    ("sensibilidad_frio", "¿Tiene sensibilidad dental al frio?"),
    ("sensibilidad_calor", "¿Tiene sensibilidad dental al calor?"),
    ("sensibilidad_masticar", "¿Tiene sensibilidad dental al masticar?"),
    ("encia_inflamada", "¿Ha notado la encia inflamada?"),
    ("sangrado_cepillado", "¿Le sangran las encias al cepillarse?"),
    ("movilidad_dientes", "¿Ha notado movilidad en sus dientes?"),
    ("cambio_posicion_dientes", "¿Ha notado cambio de posicion en sus dientes?"),
    ("mal_aliento", "¿Padece de mal aliento?"),
    ("cepilla_diario", "¿Se cepilla los dientes diariamente?"),
    ("comezon_encias", "¿Siente comezon en las encias?"),
    ("satisfecho_apariencia", "¿Esta satisfecho con la apariencia de sus dientes?"),
    ("respira_boca", "¿Respira por la boca?"),
    ("interes_conservar_dientes", "¿Tiene interes en conservar sus dientes?"),
    ("miedo_tratamiento", "¿Tiene miedo al tratamiento dental?"),
    ("ortodoncia_previa", "¿Ha usado ortodoncia (brackets/aparatos) previamente?"),
    ("mastica_todos_dientes", "¿Mastica con todos sus dientes?"),
    ("bruxismo", "¿Aprieta o rechina los dientes (bruxismo)?"),
    ("tratamiento_medico_actual", "¿Esta bajo tratamiento medico actualmente?"),
    ("sangra_facil_heridas", "¿Sangra facilmente de alguna herida?"),
    ("mala_experiencia_anestesia", "¿Ha tenido una mala experiencia con la anestesia?"),
    ("alergico_medicamento", "¿Es alergico a algun medicamento?"),
    ("operado_alguna_vez", "¿Ha sido operado alguna vez?"),
    ("utiliza_hormonas", "¿Utiliza hormonas?"),
    ("medicamento_bajar_peso", "¿Toma algun medicamento para bajar de peso?"),
    ("perdida_peso_no_intencional", "¿Ha tenido perdida de peso no intencional?"),
    ("embarazada", "¿Esta embarazada? (solo mujeres)"),
    ("toma_anticonceptivos", "¿Toma anticonceptivos? (solo mujeres)"),
    ("fuma", "¿Fuma?"),
    ("consume_alcohol", "¿Consume alcohol?"),
    ("otro_habito_dano", "¿Tiene algun otro habito que le cause dano?"),
)
PERIODONTAL_ANAMNESIS_QUESTION_CODES: frozenset[str] = frozenset(
    code for code, _ in PERIODONTAL_ANAMNESIS_QUESTIONS
)

ORAL_HEALTH_SELF_PERCEPTION_LEVELS: tuple[str, ...] = ("buena", "regular", "mala")

# --------------------------------------------------------------------------------
# 3. Auxiliares de diagnostico -- analisis radiografico: los 5 tipos son fijos
# (no un catalogo administrable, lo dice la especificacion).
# --------------------------------------------------------------------------------

RADIOGRAPHIC_FINDING_TYPES: tuple[str, ...] = (
    "perdida_osea_horizontal",
    "perdida_osea_vertical",
    "alteraciones_forma_longitud_radicular",
    "ensanchamiento_ligamento_periodontal",
    "hallazgos",
)

# --------------------------------------------------------------------------------
# 4. Odontograma de diagnostico -- datos complementarios: clasificacion de
# Kennedy (I/II/III -- la IV no aplica a los formatos revisados, ver
# docs/PENDIENTES_CLINICOS.md si la clinica real la requiere).
# --------------------------------------------------------------------------------

KENNEDY_CLASSES: tuple[str, ...] = ("I", "II", "III")

# --------------------------------------------------------------------------------
# 7/8. Diagnostico y plan de tratamiento por organo dental: solo piezas FDI
# permanentes (11-18/21-28/31-38/41-48), reutilizando el catalogo de piezas de
# app.modules.odontogram en vez de duplicarlo.
# --------------------------------------------------------------------------------

TOOTH_FDI_PERMANENT_CODES: frozenset[str] = frozenset(str(t) for t in TOOTH_FDI_PERMANENT)


def is_valid_permanent_tooth_code(tooth_fdi: str) -> bool:
    return tooth_fdi in TOOTH_FDI_PERMANENT_CODES


# --------------------------------------------------------------------------------
# Fase E (Historia Clinica Pediatrica): el plan de tratamiento por organo
# dental (`ToothTreatmentPlanEntry`) se reutiliza tambien para el plan
# pediatrico permanente/temporal (pares 11|51, 12|52, etc.) -- a diferencia de
# `ToothDiagnosisEntry` y `fixed_prosthesis_analysis`, que siguen aceptando
# SOLO piezas permanentes (diagnostico y analisis protesico no aplican a
# piezas temporales en los formatos revisados). Se amplia aqui, sin duplicar
# `TOOTH_FDI_ALL` de app.modules.odontogram.rules.
# --------------------------------------------------------------------------------

TOOTH_FDI_ALL_CODES: frozenset[str] = frozenset(str(t) for t in TOOTH_FDI_ALL)


def is_valid_tooth_code(tooth_fdi: str) -> bool:
    return tooth_fdi in TOOTH_FDI_ALL_CODES
