"""branding: corrige contraste WCAG de 4 presets (azul_sereno, aqua_suave,
lavanda_suave, verde_salvia)

Revision ID: 2b8e5f6a1c90
Revises: 9f3a1c7b2d4e
Create Date: 2026-10-06 00:20:00.000000

accessibility.spec.ts (axe-core) encontro que el color primario de estos 4 presets
no llegaba al contraste WCAG 4.5:1 contra blanco/--color-bg ni como texto blanco
sobre el boton primario (misma clase de bug que menta_clinica, Fase 12, que si se
habia corregido). Como el color de una sucursal se copia al guardarse (columna
`colors`, no una referencia viva al catalogo de presets), corregir
app/modules/branding/presets.py no alcanza para una sucursal que ya habia elegido
alguno de estos presets -- esta migracion actualiza solo las filas cuyo `primary`
siga siendo exactamente el valor original de ese preset (si alguien ya lo cambio a
mano por otra cosa, no se toca).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2b8e5f6a1c90"
down_revision: str | None = "9f3a1c7b2d4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (preset, primario original, primario corregido) -- mismos valores que
# app/modules/branding/presets.py.
FIXES: list[tuple[str, str, str]] = [
    ("azul_sereno", "#3A7FC1", "#3575B1"),
    ("aqua_suave", "#1FA2B8", "#167484"),
    ("lavanda_suave", "#7B7FD4", "#5C61CA"),
    ("verde_salvia", "#6A9E7F", "#507B61"),
]

branding_table = sa.table(
    "clinic_branding",
    sa.column("clinic_id", sa.UUID()),
    sa.column("preset", sa.String()),
    sa.column("colors", sa.JSON()),
)


def upgrade() -> None:
    conn = op.get_bind()
    for preset, old_primary, new_primary in FIXES:
        conn.execute(
            sa.text(
                """
                UPDATE clinic_branding
                SET colors = jsonb_set(colors, '{primary}', to_jsonb(cast(:new_primary as text)))
                WHERE preset = :preset AND colors->>'primary' = :old_primary
                """
            ),
            {"preset": preset, "old_primary": old_primary, "new_primary": new_primary},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for preset, old_primary, new_primary in FIXES:
        conn.execute(
            sa.text(
                """
                UPDATE clinic_branding
                SET colors = jsonb_set(colors, '{primary}', to_jsonb(cast(:old_primary as text)))
                WHERE preset = :preset AND colors->>'primary' = :new_primary
                """
            ),
            {"preset": preset, "old_primary": old_primary, "new_primary": new_primary},
        )
