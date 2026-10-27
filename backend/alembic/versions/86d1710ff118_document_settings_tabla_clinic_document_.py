"""document_settings: tabla clinic_document_settings y permiso document_settings.manage

Revision ID: 86d1710ff118
Revises: 7d52d166cfc5
Create Date: 2026-10-26 14:41:11.900099

Fase A (rediseno del expediente, docs/clinica): "Formatos de documentos"
-- logos izquierdo/derecho, titulo institucional y lugar para el encabezado
de todo PDF (ver app/modules/documents/pdf_header.py). Mismo patron que
branding (ClinicBranding/branding.manage): permiso nuevo solo para
superadmin/admin_clinica (CLAUDE.md sec. 5 y 9), insertado de forma
incremental (no se recrea el catalogo completo), igual que
4d7a2e9c15f3_catalogs_clinic_catalog_items.py.

Nota: el autogenerate tambien detecto 'ix_patients_full_name_trgm' como
"a eliminar" -- es el falso positivo ya documentado en
app/modules/patients/models.py, se quita a mano de esta migracion.
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "86d1710ff118"
down_revision: str | None = "7d52d166cfc5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_PERMISSION_CODE = "document_settings.manage"
NEW_PERMISSION_DESCRIPTION = (
    "Editar los logos, titulo institucional y lugar del encabezado de los" " documentos impresos"
)
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
    op.create_table(
        "clinic_document_settings",
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("logo_left_path", sa.String(length=500), nullable=True),
        sa.Column("logo_right_path", sa.String(length=500), nullable=True),
        sa.Column("institutional_title", sa.String(length=300), nullable=True),
        sa.Column("place_label", sa.String(length=150), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("clinic_id"),
    )

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
    op.drop_table("clinic_document_settings")
