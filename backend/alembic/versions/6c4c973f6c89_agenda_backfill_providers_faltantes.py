"""agenda: backfill de Provider faltantes para usuarios clinicos existentes

Revision ID: 6c4c973f6c89
Revises: 292f1667ef4d
Create Date: 2026-10-06 00:00:00.000000

Correccion A1 (docs/06_INSTRUCCIONES...): crear un usuario con rol odontologo o
especialista nunca creaba su Provider (entidad agendable, distinta de User desde la
Fase 6), asi que no aparecia en la agenda. A partir de ahora el codigo lo crea solo
(app/modules/iam/service.py), pero los usuarios clinicos que ya existian antes de este
cambio se quedaron sin Provider -- esta migracion de datos los completa. Nunca borra ni
recrea un Provider existente: solo inserta los que faltan.
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6c4c973f6c89"
down_revision: str | None = "292f1667ef4d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PROVIDER_ROLES = ("odontologo", "especialista")

# Misma paleta que app/modules/agenda/rules.py::PROVIDER_COLOR_PALETTE -- duplicada a
# proposito (convencion de este proyecto para migraciones de datos, ver
# e4823992f9d7_iam_agrega_permisos_diagnosis_read_y_.py): una migracion no debe
# depender del codigo de la aplicacion, que puede cambiar despues sin tocar el pasado.
PROVIDER_COLOR_PALETTE = (
    "#2BB3A3",
    "#4A90C2",
    "#E0A100",
    "#D64545",
    "#7B7FD4",
    "#3BA55C",
    "#F2A65A",
    "#5BBFD6",
)

users_table = sa.table("user_clinics", sa.column("user_id", sa.UUID()), sa.column("clinic_id", sa.UUID()), sa.column("role_id", sa.UUID()))
roles_table = sa.table("roles", sa.column("id", sa.UUID()), sa.column("code", sa.String()))
providers_table = sa.table(
    "providers",
    sa.column("id", sa.UUID()),
    sa.column("clinic_id", sa.UUID()),
    sa.column("user_id", sa.UUID()),
    sa.column("color", sa.String()),
    sa.column("is_active", sa.Boolean()),
)


def upgrade() -> None:
    conn = op.get_bind()

    clinical_memberships = conn.execute(
        sa.select(users_table.c.clinic_id, users_table.c.user_id)
        .select_from(users_table.join(roles_table, roles_table.c.id == users_table.c.role_id))
        .where(roles_table.c.code.in_(PROVIDER_ROLES))
    ).all()

    existing_providers = {
        (row.clinic_id, row.user_id)
        for row in conn.execute(sa.select(providers_table.c.clinic_id, providers_table.c.user_id))
    }

    providers_per_clinic: dict = {}
    rows_to_insert = []
    for clinic_id, user_id in clinical_memberships:
        if (clinic_id, user_id) in existing_providers:
            continue
        index = providers_per_clinic.get(clinic_id, 0)
        providers_per_clinic[clinic_id] = index + 1
        rows_to_insert.append(
            {
                "id": uuid.uuid4(),
                "clinic_id": clinic_id,
                "user_id": user_id,
                "color": PROVIDER_COLOR_PALETTE[index % len(PROVIDER_COLOR_PALETTE)],
                "is_active": True,
            }
        )
        # Para que dos usuarios sin Provider en la misma corrida no reciban el mismo
        # color, aunque list_providers() no se haya vuelto a consultar todavia.
        existing_providers.add((clinic_id, user_id))

    if rows_to_insert:
        op.bulk_insert(providers_table, rows_to_insert)


def downgrade() -> None:
    # No reversible de forma segura: no hay como distinguir un Provider creado por
    # esta migracion de uno creado despues a mano por el mismo (clinic_id, user_id).
    # Igual que otras migraciones de datos de este proyecto, downgrade no borra nada.
    pass
