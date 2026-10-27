"""catalogs: backfill parentescos, condiciones heredofamiliares, enfermedades patologicas y aparatos y sistemas

Revision ID: 7f28821611b0
Revises: 69ef0846b071
Create Date: 2026-10-26 14:52:09.487052

Fase A (rediseno del expediente, docs/clinica): catalogos administrables
nuevos para la Historia Clinica General (parentescos, condiciones
heredofamiliares, enfermedades patologicas personales y padecimientos por
aparato/sistema). Mismo patron que 4d7a2e9c15f3_catalogs_clinic_catalog_items.py:
copia congelada de app/seed.py::CATALOG_SEEDS tal como estaba en esta fecha
(una migracion no debe depender del codigo de la aplicacion, que sigue
cambiando despues sin tocar el pasado). Valores por defecto razonables,
pendientes de validar con la clinica real (ver docs/PENDIENTES_CLINICOS.md).
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "7f28821611b0"
down_revision: str | None = "69ef0846b071"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (catalog_type, code, name, sort_order, extra)
CATALOG_SEEDS: list[tuple[str, str, str, int, dict]] = [
    ("family_relationship", "padre", "Padre", 0, {}),
    ("family_relationship", "madre", "Madre", 1, {}),
    ("family_relationship", "hermano_a", "Hermano(a)", 2, {}),
    ("family_relationship", "abuelo_paterno", "Abuelo paterno", 3, {}),
    ("family_relationship", "abuela_paterna", "Abuela paterna", 4, {}),
    ("family_relationship", "abuelo_materno", "Abuelo materno", 5, {}),
    ("family_relationship", "abuela_materna", "Abuela materna", 6, {}),
    (
        "family_condition",
        "diabetes_mellitus",
        "Diabetes mellitus",
        0,
        {"alert_label": "Antecedente heredofamiliar de diabetes"},
    ),
    (
        "family_condition",
        "hipertension",
        "Hipertension",
        1,
        {"alert_label": "Antecedente heredofamiliar de hipertension"},
    ),
    ("family_condition", "enfermedades_renales", "Enfermedades renales", 2, {}),
    ("family_condition", "ets", "Enfermedades de transmision sexual", 3, {}),
    ("family_condition", "hepatitis_abc", "Hepatitis A, B o C", 4, {}),
    ("family_condition", "cancer", "Cancer", 5, {}),
    ("family_condition", "epilepsia", "Epilepsia", 6, {}),
    ("family_condition", "tuberculosis", "Tuberculosis", 7, {}),
    ("family_condition", "cardiopatias", "Cardiopatias", 8, {}),
    ("family_condition", "artritis", "Artritis", 9, {}),
    ("family_condition", "malformaciones", "Malformaciones congenitas", 10, {}),
    ("family_condition", "discapacidad_fisica", "Discapacidad fisica", 11, {}),
    ("family_condition", "padecimientos_psicologicos", "Padecimientos psicologicos", 12, {}),
    ("family_condition", "alcoholismo", "Alcoholismo", 13, {}),
    ("family_condition", "tabaquismo", "Tabaquismo", 14, {}),
    ("family_condition", "aparentemente_sano", "Aparentemente sano", 15, {}),
    (
        "pathological_condition",
        "diabetes",
        "Diabetes",
        0,
        {"alert_label": "Paciente con diabetes"},
    ),
    (
        "pathological_condition",
        "hipertension",
        "Hipertension",
        1,
        {"alert_label": "Paciente hipertenso"},
    ),
    ("pathological_condition", "enfermedades_renales", "Enfermedades renales", 2, {}),
    ("pathological_condition", "ets", "Enfermedades de transmision sexual", 3, {}),
    (
        "pathological_condition",
        "hepatitis",
        "Hepatitis",
        4,
        {"alert_label": "Paciente con hepatitis"},
    ),
    ("pathological_condition", "cancer", "Cancer", 5, {}),
    (
        "pathological_condition",
        "epilepsia",
        "Epilepsia",
        6,
        {"alert_label": "Paciente con epilepsia"},
    ),
    ("pathological_condition", "tuberculosis", "Tuberculosis", 7, {}),
    (
        "pathological_condition",
        "cardiopatias",
        "Cardiopatias",
        8,
        {"alert_label": "Paciente con cardiopatia"},
    ),
    ("pathological_condition", "artritis", "Artritis", 9, {}),
    ("pathological_condition", "malformaciones", "Malformaciones congenitas", 10, {}),
    ("pathological_condition", "discapacidad_fisica", "Discapacidad fisica", 11, {}),
    (
        "pathological_condition",
        "padecimientos_psicologicos",
        "Padecimientos psicologicos",
        12,
        {},
    ),
    ("pathological_condition", "depresion", "Depresion", 13, {}),
    ("pathological_condition", "varicela", "Varicela", 14, {}),
    ("pathological_condition", "viruela", "Viruela", 15, {}),
    ("pathological_condition", "otro", "Otro", 16, {}),
    ("systems_review_finding", "anemia", "Anemia", 0, {"system": "hematologico"}),
    (
        "systems_review_finding",
        "hemorragias_frecuentes",
        "Hemorragias frecuentes",
        1,
        {"system": "hematologico"},
    ),
    ("systems_review_finding", "transfusiones", "Transfusiones", 2, {"system": "hematologico"}),
    (
        "systems_review_finding",
        "hipertension_cv",
        "Hipertension",
        3,
        {"system": "cardiovascular"},
    ),
    (
        "systems_review_finding",
        "soplo_cardiaco",
        "Soplo cardiaco",
        4,
        {"system": "cardiovascular"},
    ),
    (
        "systems_review_finding",
        "fiebre_reumatica",
        "Fiebre reumatica",
        5,
        {"system": "cardiovascular"},
    ),
    ("systems_review_finding", "arritmias", "Arritmias", 6, {"system": "cardiovascular"}),
    ("systems_review_finding", "convulsiones", "Convulsiones", 7, {"system": "neurologico"}),
    ("systems_review_finding", "desmayos", "Desmayos", 8, {"system": "neurologico"}),
    ("systems_review_finding", "migrana", "Migrana", 9, {"system": "neurologico"}),
    ("systems_review_finding", "paralisis", "Paralisis", 10, {"system": "neurologico"}),
    ("systems_review_finding", "diabetes_endocrino", "Diabetes", 11, {"system": "endocrino"}),
    (
        "systems_review_finding",
        "trastornos_tiroideos",
        "Trastornos tiroideos",
        12,
        {"system": "endocrino"},
    ),
    (
        "systems_review_finding",
        "trastornos_crecimiento",
        "Trastornos del crecimiento",
        13,
        {"system": "endocrino"},
    ),
    ("systems_review_finding", "asma", "Asma", 14, {"system": "respiratorio"}),
    ("systems_review_finding", "bronquitis", "Bronquitis", 15, {"system": "respiratorio"}),
    (
        "systems_review_finding",
        "tuberculosis_resp",
        "Tuberculosis",
        16,
        {"system": "respiratorio"},
    ),
    ("systems_review_finding", "sinusitis", "Sinusitis", 17, {"system": "respiratorio"}),
    (
        "systems_review_finding",
        "infecciones_urinarias",
        "Infecciones urinarias",
        18,
        {"system": "genitourinario"},
    ),
    (
        "systems_review_finding",
        "insuficiencia_renal",
        "Insuficiencia renal",
        19,
        {"system": "genitourinario"},
    ),
    (
        "systems_review_finding",
        "calculos_renales",
        "Calculos renales",
        20,
        {"system": "genitourinario"},
    ),
]

NEW_CATALOG_TYPES = (
    "family_relationship",
    "family_condition",
    "pathological_condition",
    "systems_review_finding",
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
