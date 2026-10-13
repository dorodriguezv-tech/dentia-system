"""iam agrega user_preferences (B7)

Revision ID: 153986311f9b
Revises: 45ff03883321
Create Date: 2026-10-13 10:12:28.831645

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '153986311f9b'
down_revision: str | None = '45ff03883321'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # B7 (docs/06_APP_MOVIL_V1_1_PARIDAD.md sec. 4): preferencias personales del
    # usuario, compartidas entre web, tablet y telefono.
    op.create_table('user_preferences',
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('language', sa.String(length=10), server_default='es-MX', nullable=False),
    sa.Column('theme', sa.String(length=10), server_default='system', nullable=False),
    sa.Column('dentia_enabled', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('voice_id', sa.String(length=200), nullable=True),
    sa.Column('speech_rate', sa.Float(), server_default='1.0', nullable=False),
    sa.Column('speech_volume', sa.Float(), server_default='1.0', nullable=False),
    sa.Column('lock_timeout_minutes', sa.Integer(), server_default='2', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    # NO se incluye el 'ix_patients_full_name_trgm' que el autogenerate propuso
    # borrar (CLAUDE.md sec. 7, regla 4; mismo caso que en 45ff03883321): es un
    # indice GIN trigram escrito a mano que SQLAlchemy no modela.


def downgrade() -> None:
    op.drop_table('user_preferences')
