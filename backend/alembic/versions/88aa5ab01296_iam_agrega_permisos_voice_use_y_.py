"""iam: agrega permisos voice.use y voice.clinical (Fase 13, Parte C, 13.1)

Revision ID: 88aa5ab01296
Revises: eed6e0ffc7ee
Create Date: 2026-10-07 09:00:00.000000

El asistente de voz "Dentia" (docs/05_ASISTENTE_DENTIA_VOZ_CONVERSACIONAL.md,
docs/06_INSTRUCCIONES_CLAUDE_CODE_CORRECCIONES_Y_FASE13.md sec. C1) exige dos
permisos nuevos: `voice.use` (navegacion, agenda y pacientes por voz) y
`voice.clinical` (ademas, captura de datos clinicos -- odontograma,
diagnosticos, etc.). Insert incremental, no se recrea el catalogo completo.
Asignacion exacta de la tabla de la sec. C1: odontologo y especialista con
ambos permisos; recepcion solo con voice.use; caja/admin_clinica/superadmin
sin ninguno (activable despues); asistente tampoco (no esta en esa tabla,
ver docs/PENDIENTES_CLINICOS.md #36 -- se deja fuera por defecto, no se
asume que hereda el acceso de odontologo).
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "88aa5ab01296"
down_revision: str | None = "eed6e0ffc7ee"
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
    "voice.use": "Usar el asistente de voz Dentia (navegacion, agenda y pacientes)",
    "voice.clinical": "Usar Dentia para capturar datos clinicos (odontograma, diagnosticos...)",
}
NEW_ROLE_PERMISSIONS = {
    "odontologo": ("voice.use", "voice.clinical"),
    "especialista": ("voice.use", "voice.clinical"),
    "recepcion": ("voice.use",),
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
