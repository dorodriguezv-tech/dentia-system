"""catalogs: backfill craneo, biotipo facial y preguntas de anamnesis periodontal

Revision ID: b052393edaf4
Revises: a7382cfd3971
Create Date: 2026-10-26 18:30:00.000000

Fase C (rediseno del expediente, docs/clinica): catalogos administrables
nuevos para la Historia Clinica Odontologica (tipo de craneo, biotipo facial
y las 30 preguntas de la anamnesis periodontal -- cuestionario de entrevista,
no sondeo clinico). Mismo patron que 7f28821611b0_catalogs_backfill_parentescos_.py:
copia congelada de app/seed.py::CATALOG_SEEDS tal como estaba en esta fecha
(una migracion no debe depender del codigo de la aplicacion, que sigue
cambiando despues sin tocar el pasado). Valores por defecto razonables,
pendientes de validar con la clinica real (ver docs/PENDIENTES_CLINICOS.md).

Nota de discrepancia documentada en app/modules/odontological_history/rules.py:
la especificacion menciona "32 preguntas" pero enumera explicitamente solo 30
codigos (la pregunta 1 del PDF original se reparte en 3 sub-respuestas:
sensibilidad_frio/calor/masticar). Se siguio la lista literal de codigos.
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b052393edaf4"
down_revision: str | None = "a7382cfd3971"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (catalog_type, code, name, sort_order, extra)
CATALOG_SEEDS: list[tuple[str, str, str, int, dict]] = [
    ("skull_type", "mesocefalo", "Mesocefalo", 0, {}),
    ("skull_type", "braquicefalo", "Braquicefalo", 1, {}),
    ("skull_type", "dolicocefalo", "Dolicocefalo", 2, {}),
    ("facial_biotype", "mesofacial", "Mesofacial", 0, {}),
    ("facial_biotype", "braquifacial", "Braquifacial", 1, {}),
    ("facial_biotype", "dolicofacial", "Dolicofacial", 2, {}),
    (
        "periodontal_anamnesis_question",
        "sensibilidad_frio",
        "¿Tiene sensibilidad dental al frio?",
        0,
        {},
    ),
    (
        "periodontal_anamnesis_question",
        "sensibilidad_calor",
        "¿Tiene sensibilidad dental al calor?",
        1,
        {},
    ),
    (
        "periodontal_anamnesis_question",
        "sensibilidad_masticar",
        "¿Tiene sensibilidad dental al masticar?",
        2,
        {},
    ),
    ("periodontal_anamnesis_question", "encia_inflamada", "¿Ha notado la encia inflamada?", 3, {}),
    (
        "periodontal_anamnesis_question",
        "sangrado_cepillado",
        "¿Le sangran las encias al cepillarse?",
        4,
        {},
    ),
    (
        "periodontal_anamnesis_question",
        "movilidad_dientes",
        "¿Ha notado movilidad en sus dientes?",
        5,
        {},
    ),
    (
        "periodontal_anamnesis_question",
        "cambio_posicion_dientes",
        "¿Ha notado cambio de posicion en sus dientes?",
        6,
        {},
    ),
    ("periodontal_anamnesis_question", "mal_aliento", "¿Padece de mal aliento?", 7, {}),
    (
        "periodontal_anamnesis_question",
        "cepilla_diario",
        "¿Se cepilla los dientes diariamente?",
        8,
        {},
    ),
    ("periodontal_anamnesis_question", "comezon_encias", "¿Siente comezon en las encias?", 9, {}),
    (
        "periodontal_anamnesis_question",
        "satisfecho_apariencia",
        "¿Esta satisfecho con la apariencia de sus dientes?",
        10,
        {},
    ),
    ("periodontal_anamnesis_question", "respira_boca", "¿Respira por la boca?", 11, {}),
    (
        "periodontal_anamnesis_question",
        "interes_conservar_dientes",
        "¿Tiene interes en conservar sus dientes?",
        12,
        {},
    ),
    (
        "periodontal_anamnesis_question",
        "miedo_tratamiento",
        "¿Tiene miedo al tratamiento dental?",
        13,
        {},
    ),
    (
        "periodontal_anamnesis_question",
        "ortodoncia_previa",
        "¿Ha usado ortodoncia (brackets/aparatos) previamente?",
        14,
        {},
    ),
    (
        "periodontal_anamnesis_question",
        "mastica_todos_dientes",
        "¿Mastica con todos sus dientes?",
        15,
        {},
    ),
    (
        "periodontal_anamnesis_question",
        "bruxismo",
        "¿Aprieta o rechina los dientes (bruxismo)?",
        16,
        {},
    ),
    (
        "periodontal_anamnesis_question",
        "tratamiento_medico_actual",
        "¿Esta bajo tratamiento medico actualmente?",
        17,
        {},
    ),
    (
        "periodontal_anamnesis_question",
        "sangra_facil_heridas",
        "¿Sangra facilmente de alguna herida?",
        18,
        {},
    ),
    (
        "periodontal_anamnesis_question",
        "mala_experiencia_anestesia",
        "¿Ha tenido una mala experiencia con la anestesia?",
        19,
        {},
    ),
    (
        "periodontal_anamnesis_question",
        "alergico_medicamento",
        "¿Es alergico a algun medicamento?",
        20,
        {},
    ),
    (
        "periodontal_anamnesis_question",
        "operado_alguna_vez",
        "¿Ha sido operado alguna vez?",
        21,
        {},
    ),
    ("periodontal_anamnesis_question", "utiliza_hormonas", "¿Utiliza hormonas?", 22, {}),
    (
        "periodontal_anamnesis_question",
        "medicamento_bajar_peso",
        "¿Toma algun medicamento para bajar de peso?",
        23,
        {},
    ),
    (
        "periodontal_anamnesis_question",
        "perdida_peso_no_intencional",
        "¿Ha tenido perdida de peso no intencional?",
        24,
        {},
    ),
    ("periodontal_anamnesis_question", "embarazada", "¿Esta embarazada? (solo mujeres)", 25, {}),
    (
        "periodontal_anamnesis_question",
        "toma_anticonceptivos",
        "¿Toma anticonceptivos? (solo mujeres)",
        26,
        {},
    ),
    ("periodontal_anamnesis_question", "fuma", "¿Fuma?", 27, {}),
    ("periodontal_anamnesis_question", "consume_alcohol", "¿Consume alcohol?", 28, {}),
    (
        "periodontal_anamnesis_question",
        "otro_habito_dano",
        "¿Tiene algun otro habito que le cause dano?",
        29,
        {},
    ),
]

NEW_CATALOG_TYPES = (
    "skull_type",
    "facial_biotype",
    "periodontal_anamnesis_question",
)

clinics_table = sa.table("clinics", sa.column("id", sa.UUID()))
catalog_items_table = sa.table(
    "clinic_catalog_items",
    sa.column("id", sa.UUID()),
    sa.column("clinic_id", sa.UUID()),
    sa.column("catalog_type", sa.String()),
    sa.column("code", sa.String()),
    sa.column("name", sa.String()),
    sa.column("is_active", sa.Boolean()),
    sa.column("sort_order", sa.Integer()),
    sa.column("extra", postgresql.JSONB()),
)


def upgrade() -> None:
    conn = op.get_bind()
    clinic_ids = [row.id for row in conn.execute(sa.select(clinics_table.c.id))]
    rows_to_insert = [
        {
            "id": uuid.uuid4(),
            "clinic_id": clinic_id,
            "catalog_type": catalog_type,
            "code": code,
            "name": name,
            "is_active": True,
            "sort_order": sort_order,
            "extra": extra,
        }
        for clinic_id in clinic_ids
        for catalog_type, code, name, sort_order, extra in CATALOG_SEEDS
    ]
    if rows_to_insert:
        op.bulk_insert(catalog_items_table, rows_to_insert)


def downgrade() -> None:
    op.execute(
        sa.delete(catalog_items_table).where(
            catalog_items_table.c.catalog_type.in_(NEW_CATALOG_TYPES)
        )
    )
