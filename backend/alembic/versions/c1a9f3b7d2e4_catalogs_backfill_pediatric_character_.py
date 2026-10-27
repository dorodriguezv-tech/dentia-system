"""catalogs: backfill caracter pediatrico, planos terminales y anomalias del odontograma pediatrico

Revision ID: c1a9f3b7d2e4
Revises: 914ebc0df26e
Create Date: 2026-10-26 19:30:00.000000

Fase E (rediseno del expediente, docs/clinica): catalogos administrables
nuevos para la Historia Clinica Pediatrica (caracter del paciente pediatrico,
planos terminales de la oclusion, y las 10 anomalias del odontograma
pediatrico -- incluye `ausente_congenito`/`ausente_adquirida`, exclusivas de
esta historia, NO el catalogo global `odontogram_finding` de la Fase B).
Mismo patron que b052393edaf4_catalogs_backfill_craneo_biotipo_facial_.py:
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

revision: str = "c1a9f3b7d2e4"
down_revision: str | None = "914ebc0df26e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (catalog_type, code, name, sort_order, extra)
CATALOG_SEEDS: list[tuple[str, str, str, int, dict]] = [
    ("pediatric_character", "apatico", "Apatico", 0, {}),
    ("pediatric_character", "introvertido_moderado", "Introvertido moderado", 1, {}),
    ("pediatric_character", "inquieto", "Inquieto", 2, {}),
    ("pediatric_character", "irritable", "Irritable", 3, {}),
    ("pediatric_character", "hiperactivo", "Hiperactivo", 4, {}),
    ("pediatric_character", "agresivo", "Agresivo", 5, {}),
    ("terminal_plane", "recto", "Recto", 0, {}),
    ("terminal_plane", "mesial", "Mesial", 1, {}),
    ("terminal_plane", "distal", "Distal", 2, {}),
    ("pediatric_tooth_anomaly", "diente_fusionado", "Diente fusionado (fu)", 0, {}),
    ("pediatric_tooth_anomaly", "geminacion_dentinaria", "Geminacion dentinaria (Gem)", 1, {}),
    ("pediatric_tooth_anomaly", "diente_supernumerario", "Diente supernumerario (Sn)", 2, {}),
    ("pediatric_tooth_anomaly", "hipoplasia", "Hipoplasia (Hip)", 3, {}),
    ("pediatric_tooth_anomaly", "diente_traumatizado", "Diente traumatizado (tr)", 4, {}),
    ("pediatric_tooth_anomaly", "cerca_exfoliacion", "Cerca de exfoliacion (CEx)", 5, {}),
    ("pediatric_tooth_anomaly", "movilidad", "Movilidad en el diente (MV)", 6, {}),
    ("pediatric_tooth_anomaly", "inflamacion_gingival", "Inflamacion Gingival (PMA)", 7, {}),
    ("pediatric_tooth_anomaly", "ausente_congenito", "Ausente (congenito)", 8, {}),
    (
        "pediatric_tooth_anomaly",
        "ausente_adquirida",
        "Ausente por extraccion o exfoliacion",
        9,
        {},
    ),
]

NEW_CATALOG_TYPES = (
    "pediatric_character",
    "terminal_plane",
    "pediatric_tooth_anomaly",
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
