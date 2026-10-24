"""iam agrega password_history a users

Revision ID: b4b544ed1c4c
Revises: 153986311f9b
Create Date: 2026-10-24 00:53:15.043847

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'b4b544ed1c4c'
down_revision: str | None = '153986311f9b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Nota: el autogenerate tambien proponia aqui un DROP del indice trigram
# ix_patients_full_name_trgm de patients; es un falso positivo ya documentado
# (el indice sigue existiendo desde la migracion 0079b0a977a3) -- se omite a
# proposito, igual que en e5bcac246c11.


def upgrade() -> None:
    # server_default='[]' para que las filas existentes (usuarios ya creados)
    # queden con historial vacio en vez de fallar el NOT NULL.
    op.add_column(
        'users',
        sa.Column(
            'password_history',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='[]',
        ),
    )


def downgrade() -> None:
    op.drop_column('users', 'password_history')
