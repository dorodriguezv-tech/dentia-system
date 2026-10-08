"""voice: voice_command_logs (Fase 13, Parte C, 13.1 "Base de voz")

Revision ID: dc1338359268
Revises: 88aa5ab01296
Create Date: 2026-10-07 09:15:00.000000

Registro de texto de las ordenes dirigidas a Dentia (nunca el audio, nunca la
conversacion con el paciente -- ver app/voice/models.py). Append-only, sin
AuditedMixin (no tiene created_by/updated_at: el "actor" ya es `user_id`, y una
fila de este log nunca se edita despues de crearse).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "dc1338359268"
down_revision: str | None = "88aa5ab01296"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "voice_command_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("event", sa.String(length=30), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("confirmation_mode", sa.String(length=20), nullable=True),
        sa.Column("result", sa.String(length=200), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_voice_command_logs_clinic_id", "voice_command_logs", ["clinic_id"])


def downgrade() -> None:
    op.drop_index("ix_voice_command_logs_clinic_id", table_name="voice_command_logs")
    op.drop_table("voice_command_logs")
