"""patients: default_resource_id y primary_provider_id (Fase 12.2, Parte B3)

Revision ID: eed6e0ffc7ee
Revises: c0d4bd3a1e2e
Create Date: 2026-10-06 20:30:00.000000

El formulario de alta de pacientes (Parte B3) deja elegir un gabinete y un
profesional tratante por defecto -- la agenda los preselecciona despues al
agendar una cita para ese paciente (NewAppointmentForm.tsx), y la pantalla de
"Mis pacientes" (filtro para el rol odontologo) se basa en
`primary_provider_id`. Columnas opcionales, sin backfill: ningun paciente
existente tiene esta asignacion todavia, es un vacio razonable.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "eed6e0ffc7ee"
down_revision: str | None = "c0d4bd3a1e2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("patients", sa.Column("default_resource_id", sa.UUID(), nullable=True))
    op.add_column("patients", sa.Column("primary_provider_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_patients_default_resource_id_resources",
        "patients",
        "resources",
        ["default_resource_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_patients_primary_provider_id_providers",
        "patients",
        "providers",
        ["primary_provider_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_patients_primary_provider_id_providers", "patients", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_patients_default_resource_id_resources", "patients", type_="foreignkey"
    )
    op.drop_column("patients", "primary_provider_id")
    op.drop_column("patients", "default_resource_id")
