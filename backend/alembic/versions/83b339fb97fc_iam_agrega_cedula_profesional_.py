"""iam: agrega cedula profesional (professional_license) a users

Revision ID: 83b339fb97fc
Revises: d6d54ce82881
Create Date: 2026-10-24 15:08:37.711124

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '83b339fb97fc'
down_revision: str | None = 'd6d54ce82881'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Nota: el autogenerate tambien proponia aqui un DROP del indice trigram
# ix_patients_full_name_trgm de patients; es un falso positivo ya documentado
# (el indice sigue existiendo desde la migracion 0079b0a977a3) -- se omite a
# proposito, igual que en e5bcac246c11 y b4b544ed1c4c.


def upgrade() -> None:
    op.add_column('users', sa.Column('professional_license', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'professional_license')
