"""iam: agrega rol demo, expires_at y is_sandboxed a users

Revision ID: 772aaf82b5db
Revises: 83b339fb97fc
Create Date: 2026-10-25 10:04:14.527637

A peticion del operador: cuenta de demostracion de tiempo limitado
(demo@prueba.com) que debe ver y poder usar TODO el sistema. A diferencia de las
migraciones incrementales anteriores (que agregan un permiso puntual a un rol
existente), el rol "demo" se define como "todos los permisos que existan en
este momento" -- se consulta la tabla `permissions` en vivo durante la
migracion (en vez de una lista congelada) porque esa es, a proposito, su
definicion: cualquier permiso nuevo que se agregue despues necesitaria su
propia migracion incremental para que "demo" lo siga teniendo, igual que
cualquier otro rol.
"""
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '772aaf82b5db'
down_revision: str | None = '83b339fb97fc'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Nota: el autogenerate tambien proponia aqui un DROP del indice trigram
# ix_patients_full_name_trgm de patients; es un falso positivo ya documentado
# (ver e5bcac246c11, b4b544ed1c4c, 83b339fb97fc) -- se omite a proposito.

roles_table = sa.table(
    "roles", sa.column("id", sa.UUID()), sa.column("code", sa.String()), sa.column("name", sa.String())
)
permissions_table = sa.table("permissions", sa.column("id", sa.UUID()), sa.column("code", sa.String()))
role_permissions_table = sa.table(
    "role_permissions",
    sa.column("role_id", sa.UUID()),
    sa.column("permission_id", sa.UUID()),
)

ROLE_CODE = "demo"
ROLE_NAME = "Demostracion (temporal)"


def upgrade() -> None:
    op.add_column("users", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    # server_default='false' para que los usuarios ya existentes queden con
    # is_sandboxed=False en vez de fallar el NOT NULL (mismo patron que
    # password_history en b4b544ed1c4c).
    op.add_column(
        "users",
        sa.Column("is_sandboxed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    conn = op.get_bind()
    role_id = uuid.uuid4()
    op.bulk_insert(roles_table, [{"id": role_id, "code": ROLE_CODE, "name": ROLE_NAME}])
    permission_ids = conn.execute(sa.select(permissions_table.c.id)).scalars().all()
    op.bulk_insert(
        role_permissions_table,
        [{"role_id": role_id, "permission_id": pid} for pid in permission_ids],
    )


def downgrade() -> None:
    conn = op.get_bind()
    role_id = conn.execute(
        sa.select(roles_table.c.id).where(roles_table.c.code == ROLE_CODE)
    ).scalar_one()
    op.execute(sa.delete(role_permissions_table).where(role_permissions_table.c.role_id == role_id))
    op.execute(sa.delete(roles_table).where(roles_table.c.id == role_id))

    op.drop_column("users", "is_sandboxed")
    op.drop_column("users", "expires_at")
