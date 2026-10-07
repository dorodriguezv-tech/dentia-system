"""agenda: Provider.default_resource_id (Fase 12.2, Parte B2)

Revision ID: c0d4bd3a1e2e
Revises: 4d7a2e9c15f3
Create Date: 2026-10-06 20:00:00.000000

El formulario de alta de usuarios (Parte B2) deja elegir, por cada sucursal
asignada, un gabinete por defecto para el profesional nuevo -- la agenda lo
preselecciona al agendar con el (ver NewAppointmentForm.tsx). Columna opcional,
sin backfill: ningun Provider existente tiene un gabinete por defecto todavia,
es un vacio razonable, no un dato que se pueda derivar de lo que ya existe.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c0d4bd3a1e2e"
down_revision: str | None = "4d7a2e9c15f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("providers", sa.Column("default_resource_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_providers_default_resource_id_resources",
        "providers",
        "resources",
        ["default_resource_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_providers_default_resource_id_resources", "providers", type_="foreignkey"
    )
    op.drop_column("providers", "default_resource_id")
