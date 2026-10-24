"""iam: el rol odontologo gana el permiso patients.write

Revision ID: d6d54ce82881
Revises: b4b544ed1c4c
Create Date: 2026-10-24 16:40:00.000000

Decision de producto (validada con el operador, CLAUDE.md sec. 7): el
odontologo tambien debe poder dar de alta y editar pacientes, no solo
verlos -- antes solo admin_clinica y recepcion tenian patients.write. El
permiso patients.write ya existe desde el seed base (c2a7f9d3e1b0); esta
migracion solo agrega la fila de role_permissions que falta, sin tocar la
tabla permissions.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d6d54ce82881"
down_revision: str | None = "b4b544ed1c4c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

roles_table = sa.table("roles", sa.column("id", sa.UUID()), sa.column("code", sa.String()))
permissions_table = sa.table(
    "permissions", sa.column("id", sa.UUID()), sa.column("code", sa.String())
)
role_permissions_table = sa.table(
    "role_permissions",
    sa.column("role_id", sa.UUID()),
    sa.column("permission_id", sa.UUID()),
)

ROLE_CODE = "odontologo"
PERMISSION_CODE = "patients.write"


def upgrade() -> None:
    conn = op.get_bind()

    role_id = conn.execute(
        sa.select(roles_table.c.id).where(roles_table.c.code == ROLE_CODE)
    ).scalar_one()
    permission_id = conn.execute(
        sa.select(permissions_table.c.id).where(permissions_table.c.code == PERMISSION_CODE)
    ).scalar_one()

    op.bulk_insert(
        role_permissions_table,
        [{"role_id": role_id, "permission_id": permission_id}],
    )


def downgrade() -> None:
    conn = op.get_bind()

    role_id = conn.execute(
        sa.select(roles_table.c.id).where(roles_table.c.code == ROLE_CODE)
    ).scalar_one()
    permission_id = conn.execute(
        sa.select(permissions_table.c.id).where(permissions_table.c.code == PERMISSION_CODE)
    ).scalar_one()

    op.execute(
        sa.delete(role_permissions_table).where(
            role_permissions_table.c.role_id == role_id,
            role_permissions_table.c.permission_id == permission_id,
        )
    )
