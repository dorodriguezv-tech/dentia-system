"""iam: agrega permiso billing.configure

Revision ID: a1c3e7f90b22
Revises: 8ba58286654b
Create Date: 2026-10-05 17:00:00.000000

La Fase 10 agrega la posibilidad de desactivar la cobranza por sucursal (para
instalaciones donde no se cobra de verdad, p.ej. clinicas universitarias de
practica -- ver docs/PENDIENTES_CLINICOS.md). Activarlo/desactivarlo es una
decision administrativa de la sucursal, no una operacion de caja del dia a dia,
asi que necesita su propio permiso en vez de reusar billing.write (que
tambien tiene "caja"). Insert incremental, mismo patron que e4823992f9d7.
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1c3e7f90b22"
down_revision: str | None = "8ba58286654b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

roles_table = sa.table("roles", sa.column("id", sa.UUID()), sa.column("code", sa.String()))
permissions_table = sa.table(
    "permissions",
    sa.column("id", sa.UUID()),
    sa.column("code", sa.String()),
    sa.column("description", sa.String()),
)
role_permissions_table = sa.table(
    "role_permissions",
    sa.column("role_id", sa.UUID()),
    sa.column("permission_id", sa.UUID()),
)

NEW_PERMISSIONS = {"billing.configure": "Activar o desactivar la cobranza de la sucursal"}
NEW_ROLE_PERMISSIONS = {"admin_clinica": ("billing.configure",)}


def upgrade() -> None:
    conn = op.get_bind()

    permission_ids = {code: uuid.uuid4() for code in NEW_PERMISSIONS}
    op.bulk_insert(
        permissions_table,
        [
            {"id": permission_ids[code], "code": code, "description": description}
            for code, description in NEW_PERMISSIONS.items()
        ],
    )

    role_id_by_code = {
        code: role_id
        for role_id, code in conn.execute(sa.select(roles_table.c.id, roles_table.c.code))
    }
    op.bulk_insert(
        role_permissions_table,
        [
            {"role_id": role_id_by_code[role_code], "permission_id": permission_ids[perm_code]}
            for role_code, perm_codes in NEW_ROLE_PERMISSIONS.items()
            for perm_code in perm_codes
        ],
    )


def downgrade() -> None:
    # role_permissions.permission_id tiene ON DELETE CASCADE: borrar el permiso
    # tambien borra sus filas de role_permissions.
    op.execute(
        sa.delete(permissions_table).where(permissions_table.c.code.in_(NEW_PERMISSIONS.keys()))
    )
