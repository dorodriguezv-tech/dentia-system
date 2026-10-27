"""odontogram: reconcilia la paleta de hallazgos con la leyenda oficial de docs/clinica

Revision ID: 9b1f4c7a0e2d
Revises: 23e4f3b41ff7
Create Date: 2026-10-26 15:30:00.000000

Fase B (odontograma nuevo: figura anatomica + catalogo de colores reconciliado). Los
PDF de referencia en docs/clinica ("historia clinca odontologica.pdf", pagina 7, y
"historia clinica general.pdf", pagina 5 -- ambos "ODONTOGRAMA DE DIAGNOSTICO") traen una
leyenda oficial de 4 colores: Rojo = caries, Azul = protesis y restauraciones,
Negro = dientes ausentes o restos radiculares, Verde = biopelicula y tartaro dental. El
catalogo de hallazgos (`clinic_catalog_items`, catalog_type="odontogram_finding") sembrado
hasta ahora (ver 4d7a2e9c15f3) no coincidia: "ausente" era gris y no existia el hallazgo
"biopelicula_tartaro". Esta migracion, mismo patron que 2b8e5f6a1c90 (jsonb_set sobre la
columna `extra` por SQL crudo, solo sobre filas cuyo color siga siendo exactamente el
original) y que 7f28821611b0 (insertar filas nuevas por clinica a partir de una copia
congelada de `app/seed.py::CATALOG_SEEDS` -- una migracion no debe depender del codigo de
la aplicacion, que sigue cambiando despues sin tocar el pasado):
  - cambia el color de "ausente" de gris (#8C8C8C) a negro (#1A1A1A) para cada clinica
    existente;
  - cambia el color de "sellador" de verde (#6AB04C) a magenta (#A8407D), porque ese verde
    ahora es exclusivo de la leyenda oficial (biopelicula/tartaro);
  - inserta el hallazgo nuevo "biopelicula_tartaro" (verde #6AB04C, el mismo que antes
    tenia "sellador") para cada clinica existente que no lo tenga ya.
"restauracion" (#4A90C2) y "protesis_fija" (#3A7FC1) ya comparten la misma familia de
azules que pide la leyenda ("Azul: protesis y restauraciones"): no se tocan. "caries" y
"extraccion_indicada" ya comparten el rojo oficial: tampoco se tocan. Cierra el pendiente
#3 de docs/PENDIENTES_CLINICOS.md ("paleta provisional, no validada con la clinica").
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "9b1f4c7a0e2d"
down_revision: str | None = "23e4f3b41ff7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CATALOG_TYPE = "odontogram_finding"

# (code, color_viejo, color_nuevo)
COLOR_FIXES: list[tuple[str, str, str]] = [
    ("ausente", "#8C8C8C", "#1A1A1A"),
    ("sellador", "#6AB04C", "#A8407D"),
]

NEW_FINDING_CODE = "biopelicula_tartaro"
NEW_FINDING_NAME = "Biopelicula y tartaro dental"
NEW_FINDING_SORT_ORDER = 12
NEW_FINDING_EXTRA = {"color": "#6AB04C", "symbol": "BT", "requires_surface": True}

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

_SET_COLOR_SQL = sa.text("""
    UPDATE clinic_catalog_items
    SET extra = jsonb_set(extra, '{color}', to_jsonb(cast(:new_color as text)))
    WHERE catalog_type = :catalog_type AND code = :code AND extra->>'color' = :old_color
    """)


def _recolor(conn, code: str, old_color: str, new_color: str) -> None:
    conn.execute(
        _SET_COLOR_SQL,
        {
            "catalog_type": CATALOG_TYPE,
            "code": code,
            "old_color": old_color,
            "new_color": new_color,
        },
    )


def upgrade() -> None:
    conn = op.get_bind()
    for code, old_color, new_color in COLOR_FIXES:
        _recolor(conn, code, old_color, new_color)

    existing_clinic_ids = {
        row.clinic_id
        for row in conn.execute(
            sa.select(catalog_items_table.c.clinic_id).where(
                catalog_items_table.c.catalog_type == CATALOG_TYPE,
                catalog_items_table.c.code == NEW_FINDING_CODE,
            )
        )
    }
    clinic_ids = [row.id for row in conn.execute(sa.select(clinics_table.c.id))]
    rows_to_insert = [
        {
            "id": uuid.uuid4(),
            "clinic_id": clinic_id,
            "catalog_type": CATALOG_TYPE,
            "code": NEW_FINDING_CODE,
            "name": NEW_FINDING_NAME,
            "is_active": True,
            "sort_order": NEW_FINDING_SORT_ORDER,
            "extra": NEW_FINDING_EXTRA,
        }
        for clinic_id in clinic_ids
        if clinic_id not in existing_clinic_ids
    ]
    if rows_to_insert:
        op.bulk_insert(catalog_items_table, rows_to_insert)


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.delete(catalog_items_table)
        .where(catalog_items_table.c.catalog_type == CATALOG_TYPE)
        .where(catalog_items_table.c.code == NEW_FINDING_CODE)
    )
    for code, old_color, new_color in COLOR_FIXES:
        _recolor(conn, code, new_color, old_color)
