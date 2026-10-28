"""iam: agrega permiso version_info.read

Revision ID: 7cc279f4a7a6
Revises: 9c1fdb20d7bc
Create Date: 2026-10-27 17:32:13.116036

Pantalla nueva "Control de versiones" (menu de administrador que muestra la
version de DentalCare desplegada, derivada de configuracion/entorno --
app/modules/version_info/). Mismo patron que
86d1710ff118_document_settings_tabla_clinic_document_.py: permiso nuevo solo
para superadmin/admin_clinica (CLAUDE.md sec. 5 y 9), insertado de forma
incremental (no se recrea el catalogo completo).
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7cc279f4a7a6"
down_revision: str | None = "9c1fdb20d7bc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_PERMISSION_CODE = "version_info.read"
NEW_PERMISSION_DESCRIPTION = "Ver la version de DentalCare desplegada"
ROLE_CODES_WITH_ACCESS = ("superadmin", "admin_clinica")

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


def upgrade() -> None:
    conn = op.get_bind()

    permission_id = uuid.uuid4()
    op.bulk_insert(
        permissions_table,
        [
            {
                "id": permission_id,
                "code": NEW_PERMISSION_CODE,
                "description": NEW_PERMISSION_DESCRIPTION,
            }
        ],
    )
    role_ids = (
        conn.execute(
            sa.select(roles_table.c.id).where(roles_table.c.code.in_(ROLE_CODES_WITH_ACCESS))
        )
        .scalars()
        .all()
    )
    op.bulk_insert(
        role_permissions_table,
        [{"role_id": role_id, "permission_id": permission_id} for role_id in role_ids],
    )

    # "demo" (Fase 12.2): tiene TODOS los permisos existentes a proposito
    # (ver app/modules/iam/permissions_catalog.py) -- si el rol ya existe en
    # esta base de datos, se le da tambien este permiso nuevo.
    demo_role_id = conn.execute(
        sa.select(roles_table.c.id).where(roles_table.c.code == "demo")
    ).scalar_one_or_none()
    if demo_role_id is not None:
        op.bulk_insert(
            role_permissions_table,
            [{"role_id": demo_role_id, "permission_id": permission_id}],
        )


def downgrade() -> None:
    # role_permissions.permission_id tiene ON DELETE CASCADE: borrar el permiso
    # tambien borra sus filas de role_permissions.
    op.execute(sa.delete(permissions_table).where(permissions_table.c.code == NEW_PERMISSION_CODE))
