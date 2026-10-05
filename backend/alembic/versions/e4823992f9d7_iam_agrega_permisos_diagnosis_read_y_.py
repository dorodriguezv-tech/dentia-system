"""iam: agrega permisos diagnosis.read y treatment.read

Revision ID: e4823992f9d7
Revises: 588ceae4a97c
Create Date: 2026-10-05 10:49:46.423412

La migracion c2a7f9d3e1b0 (Fase 1) sembro diagnosis.write/treatment.write/
treatment.accept_budget anticipando esta fase, pero sin un permiso de solo
lectura -- un vacio real del catalogo original. Se agrega aqui como un
insert incremental (no se recrea el catalogo completo) para odontologo,
especialista (diagnosis.read + treatment.read) y admin_clinica
(treatment.read, para supervisar presupuestos sin poder crearlos).
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e4823992f9d7"
down_revision: str | None = "588ceae4a97c"
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

NEW_PERMISSIONS = {
    "diagnosis.read": "Ver diagnosticos",
    "treatment.read": "Ver planes de tratamiento y presupuestos",
}
NEW_ROLE_PERMISSIONS = {
    "admin_clinica": ("treatment.read",),
    "odontologo": ("diagnosis.read", "treatment.read"),
    "especialista": ("diagnosis.read", "treatment.read"),
}


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
