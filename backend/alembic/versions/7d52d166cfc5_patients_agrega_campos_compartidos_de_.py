"""patients: agrega campos compartidos de la historia clinica general

Revision ID: 7d52d166cfc5
Revises: ceec1ae547e3
Create Date: 2026-10-26 14:38:49.644290

Fase A (rediseno del expediente segun formatos oficiales, docs/clinica):
campos compartidos que la Historia Clinica General y demas documentos
impresos necesitan autollenar desde el paciente. Todos nullable, no rompen
pacientes ya existentes.

Nota: el autogenerate tambien detecto 'ix_patients_full_name_trgm' como
"a eliminar" -- es el falso positivo ya documentado en
app/modules/patients/models.py (el indice usa la funcion SQL
immutable_unaccent, que SQLAlchemy no puede mapear como columna), asi que esa
linea se quita a mano de esta migracion.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7d52d166cfc5"
down_revision: str | None = "ceec1ae547e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("birth_place", sa.String(length=200), nullable=True))
    op.add_column("patients", sa.Column("blood_type", sa.String(length=5), nullable=True))
    op.add_column("patients", sa.Column("education_level", sa.String(length=50), nullable=True))
    op.add_column("patients", sa.Column("can_read_write", sa.Boolean(), nullable=True))
    op.add_column("patients", sa.Column("religion", sa.String(length=100), nullable=True))
    op.add_column("patients", sa.Column("ethnic_group", sa.String(length=100), nullable=True))
    op.add_column("patients", sa.Column("race", sa.String(length=100), nullable=True))
    op.add_column("patients", sa.Column("occupation", sa.String(length=150), nullable=True))
    op.add_column("patients", sa.Column("marital_status", sa.String(length=30), nullable=True))


def downgrade() -> None:
    op.drop_column("patients", "marital_status")
    op.drop_column("patients", "occupation")
    op.drop_column("patients", "race")
    op.drop_column("patients", "ethnic_group")
    op.drop_column("patients", "religion")
    op.drop_column("patients", "can_read_write")
    op.drop_column("patients", "education_level")
    op.drop_column("patients", "blood_type")
    op.drop_column("patients", "birth_place")
