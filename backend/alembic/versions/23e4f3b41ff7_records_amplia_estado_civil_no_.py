"""records_amplia_estado_civil_no_patologico

Revision ID: 23e4f3b41ff7
Revises: 7f28821611b0
Create Date: 2026-10-26 16:37:33.412538

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "23e4f3b41ff7"
down_revision: str | None = "7f28821611b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nota: autogenerate tambien detecto el indice ix_patients_full_name_trgm
    # como "a eliminar" -- es un falso positivo conocido del repo (la funcion
    # SQL immutable_unaccent no es mapeable como columna de SQLAlchemy, ver
    # comentario en patients/models.py), se quita a mano de esta migracion.
    op.alter_column(
        "personal_non_pathological_histories",
        "estado_civil",
        existing_type=sa.VARCHAR(length=20),
        type_=sa.String(length=60),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "personal_non_pathological_histories",
        "estado_civil",
        existing_type=sa.String(length=60),
        type_=sa.VARCHAR(length=20),
        existing_nullable=True,
    )
