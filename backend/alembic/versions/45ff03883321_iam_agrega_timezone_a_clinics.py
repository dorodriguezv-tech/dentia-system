"""iam agrega timezone a clinics

Revision ID: 45ff03883321
Revises: dc1338359268
Create Date: 2026-10-08 08:05:21.753804

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '45ff03883321'
down_revision: str | None = 'dc1338359268'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Bug #42 de docs/PENDIENTES_CLINICOS.md: zona horaria configurable por
    # sucursal, para que "hoy" (citas/atenciones) se calcule con la hora
    # LOCAL de la clinica, no la del servidor.
    op.add_column(
        'clinics',
        sa.Column(
            'timezone', sa.String(length=50), server_default='America/Mexico_City', nullable=False
        ),
    )
    # NO se incluye el 'ix_patients_full_name_trgm' que el autogenerate propuso
    # borrar (CLAUDE.md sec. 7, regla 4): es un indice GIN trigram escrito a
    # mano (Fase 3, busqueda tolerante de pacientes) que SQLAlchemy no modela,
    # asi que el autogenerate siempre lo ve como "sobrante" -- borrarlo
    # rompería la búsqueda de pacientes.


def downgrade() -> None:
    op.drop_column('clinics', 'timezone')
