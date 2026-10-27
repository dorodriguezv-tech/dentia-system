"""patients: agrega patient_type

Revision ID: 9c1fdb20d7bc
Revises: 32fce2f53516
Create Date: 2026-10-27 11:35:15.618002

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9c1fdb20d7bc"
down_revision: str | None = "32fce2f53516"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # NOTA (ver comentario en patients/models.py): autogenerate tambien detecto
    # "removed index ix_patients_full_name_trgm" -- ese indice GIN sobre
    # immutable_unaccent(lower(full_name)) sigue existiendo (migracion
    # 0079b0a977a3), autogenerate solo no lo reconoce porque no esta declarado
    # como Index() de SQLAlchemy. Se quito ese drop/create falso a mano.
    op.add_column("patients", sa.Column("patient_type", sa.String(length=20), nullable=True))

    # Backfill (pendiente #73 de docs/PENDIENTES_CLINICOS.md): los pacientes ya
    # existentes no tienen esta anotacion capturada a mano, asi que se calcula
    # igual que al crear/editar uno nuevo sin especificarla -- mismo corte de 12
    # anios que rules.PEDIATRIC_AGE_CUTOFF_YEARS, expresado en SQL para no
    # depender de Python en la migracion.
    op.execute("""
        UPDATE patients
        SET patient_type = CASE
            WHEN date_of_birth > (CURRENT_DATE - INTERVAL '12 years') THEN 'pediatrico'
            ELSE 'adulto'
        END
        WHERE patient_type IS NULL
        """)


def downgrade() -> None:
    op.drop_column("patients", "patient_type")
