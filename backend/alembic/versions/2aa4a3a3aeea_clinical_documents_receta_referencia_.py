"""clinical_documents: receta, referencia/interconsulta y contrarreferencia

Revision ID: 2aa4a3a3aeea
Revises: 7cc279f4a7a6
Create Date: 2026-10-27 00:00:00.000000

Fase D (docs/clinica, "Documentos imprimibles nuevos"): tablas nuevas para
Prescription/ReferralNote/CounterReferralNote (ver
app/modules/clinical_documents/models.py). A diferencia de `consents`, estos
documentos no llevan firma digital ni PDF guardado -- se generan al vuelo
cada vez que se piden (mismo patron que el presupuesto de tratamiento), asi
que no hay columnas `pdf_path`/`content_hash` aqui.

Permisos: se reutilizan `documents.read`/`documents.write` (ya existen y ya
los tienen odontologo/especialista) -- no se agrega un permiso nuevo.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "2aa4a3a3aeea"
down_revision: str | None = "7cc279f4a7a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "prescriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("encounter_id", sa.UUID(), nullable=False),
        sa.Column("folio", sa.String(length=40), nullable=False),
        sa.Column("diagnostico", sa.Text(), nullable=False),
        sa.Column("medications", JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("annul_reason", sa.Text(), nullable=True),
        sa.Column("annulled_by", sa.UUID(), nullable=True),
        sa.Column("annulled_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["annulled_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "referral_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("encounter_id", sa.UUID(), nullable=False),
        sa.Column("diagnosticos", sa.Text(), nullable=True),
        sa.Column("medicamentos_texto", sa.Text(), nullable=True),
        sa.Column("alergias_texto", sa.Text(), nullable=True),
        sa.Column("tratamientos_texto", sa.Text(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("motivo_interconsulta", sa.Text(), nullable=False),
        sa.Column("establecimiento_receptor", sa.String(length=300), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("annul_reason", sa.Text(), nullable=True),
        sa.Column("annulled_by", sa.UUID(), nullable=True),
        sa.Column("annulled_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["annulled_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "counter_referral_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("encounter_id", sa.UUID(), nullable=False),
        sa.Column("referral_note_id", sa.UUID(), nullable=True),
        sa.Column("motivo_contrarreferencia", sa.Text(), nullable=False),
        sa.Column("tratamientos_texto", sa.Text(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("motivo_interconsulta_original", sa.Text(), nullable=True),
        sa.Column("establecimiento_emisor", sa.String(length=300), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("annul_reason", sa.Text(), nullable=True),
        sa.Column("annulled_by", sa.UUID(), nullable=True),
        sa.Column("annulled_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["annulled_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["referral_note_id"], ["referral_notes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("counter_referral_notes")
    op.drop_table("referral_notes")
    op.drop_table("prescriptions")
