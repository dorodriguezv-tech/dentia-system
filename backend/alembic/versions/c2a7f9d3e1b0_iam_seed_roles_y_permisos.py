"""iam: seed de roles y permisos (CLAUDE.md sec. 5)

Revision ID: c2a7f9d3e1b0
Revises: b6c1e0a5f4ac
Create Date: 2026-10-04 19:05:00.000000

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.modules.iam.permissions_catalog import PERMISSIONS, ROLE_PERMISSIONS, ROLES

revision: str = "c2a7f9d3e1b0"
down_revision: str | None = "b6c1e0a5f4ac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

roles_table = sa.table(
    "roles",
    sa.column("id", sa.UUID()),
    sa.column("code", sa.String()),
    sa.column("name", sa.String()),
)
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
    role_ids = {code: uuid.uuid4() for code in ROLES}
    permission_ids = {code: uuid.uuid4() for code in PERMISSIONS}

    op.bulk_insert(
        roles_table,
        [{"id": role_ids[code], "code": code, "name": name} for code, name in ROLES.items()],
    )
    op.bulk_insert(
        permissions_table,
        [
            {"id": permission_ids[code], "code": code, "description": description}
            for code, description in PERMISSIONS.items()
        ],
    )
    op.bulk_insert(
        role_permissions_table,
        [
            {"role_id": role_ids[role_code], "permission_id": permission_ids[permission_code]}
            for role_code, codes in ROLE_PERMISSIONS.items()
            for permission_code in codes
        ],
    )


def downgrade() -> None:
    op.execute(sa.delete(role_permissions_table))
    op.execute(sa.delete(permissions_table))
    op.execute(sa.delete(roles_table))
