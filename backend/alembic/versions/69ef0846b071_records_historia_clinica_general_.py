"""records: historia clinica general (heredofamiliares, antecedentes personales, aparatos y sistemas) y extiende vital_signs

Revision ID: 69ef0846b071
Revises: 86d1710ff118
Create Date: 2026-10-26 14:47:36.167486

Fase A (rediseno del expediente segun formatos oficiales, docs/clinica): tablas
nuevas para la Historia Clinica General -- heredofamiliares, antecedentes
personales patologicos/no patologicos e interrogatorio por aparatos y sistemas
-- agregadas junto a medical_history/allergies/medications/vital_signs (que no
se tocan, salvo vital_signs que se extiende con columnas nuevas, todas
nullable). Mismo patron _AnnullableMixin + AuditedMixin que el resto del
modulo (regla 1 y 2 de CLAUDE.md: sin borrado fisico, se anula con motivo).

Nota: el autogenerate tambien detecto 'ix_patients_full_name_trgm' como
"a eliminar" -- es el falso positivo ya documentado en
app/modules/patients/models.py, se quita a mano de esta migracion.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "69ef0846b071"
down_revision: str | None = "86d1710ff118"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "family_history_entries",
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("encounter_id", sa.UUID(), nullable=False),
        sa.Column("relationship_code", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=15), nullable=False),
        sa.Column("conditions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("origin", sa.String(length=15), nullable=False),
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
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["annulled_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "personal_non_pathological_histories",
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("encounter_id", sa.UUID(), nullable=False),
        sa.Column("comidas_dia", sa.Integer(), nullable=True),
        sa.Column("calidad_alimentacion", sa.String(length=10), nullable=True),
        sa.Column("agua_litros_dia", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("trastornos_sueno", sa.Boolean(), nullable=False),
        sa.Column("trastornos_sueno_texto", sa.String(length=300), nullable=True),
        sa.Column("cepillados_dia", sa.Integer(), nullable=True),
        sa.Column("hilo_dental", sa.Boolean(), nullable=False),
        sa.Column("enjuague_bucal", sa.Boolean(), nullable=False),
        sa.Column("deportes", sa.Boolean(), nullable=False),
        sa.Column("deportes_cual", sa.String(length=200), nullable=True),
        sa.Column("derechohabiencia", sa.String(length=20), nullable=True),
        sa.Column("estado_civil", sa.String(length=20), nullable=True),
        sa.Column("medicamentos_suplementos", sa.Boolean(), nullable=False),
        sa.Column("medicamentos_controlados", sa.Boolean(), nullable=False),
        sa.Column("medicamentos_texto", sa.String(length=300), nullable=True),
        sa.Column("servicios_basicos", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("adicciones", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("origin", sa.String(length=15), nullable=False),
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
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["annulled_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "personal_pathological_histories",
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("encounter_id", sa.UUID(), nullable=False),
        sa.Column("dolor_masticar", sa.Boolean(), nullable=False),
        sa.Column("sensibilidad_frio", sa.Boolean(), nullable=False),
        sa.Column("sensibilidad_calor", sa.Boolean(), nullable=False),
        sa.Column("sensibilidad_dulce", sa.Boolean(), nullable=False),
        sa.Column("sensibilidad_localizacion", sa.String(length=200), nullable=True),
        sa.Column("sangrado_encias", sa.String(length=20), nullable=False),
        sa.Column("dolor_cepillado", sa.Boolean(), nullable=False),
        sa.Column("aftas_ulceras", sa.Boolean(), nullable=False),
        sa.Column("perdida_piezas", sa.Boolean(), nullable=False),
        sa.Column("perdida_piezas_causa", sa.String(length=300), nullable=True),
        sa.Column("anestesia_previa", sa.Boolean(), nullable=False),
        sa.Column("extracciones", sa.Boolean(), nullable=False),
        sa.Column("extracciones_texto", sa.String(length=300), nullable=True),
        sa.Column("complicaciones_operatorias", sa.Boolean(), nullable=False),
        sa.Column("complicaciones_operatorias_texto", sa.String(length=300), nullable=True),
        sa.Column("traumatismo_dental", sa.Boolean(), nullable=False),
        sa.Column("traumatismo_dental_texto", sa.String(length=300), nullable=True),
        sa.Column("infecciones_dentales", sa.Boolean(), nullable=False),
        sa.Column("infecciones_dentales_texto", sa.String(length=300), nullable=True),
        sa.Column("estres", sa.Boolean(), nullable=False),
        sa.Column("estres_texto", sa.String(length=300), nullable=True),
        sa.Column("hospitalizacion_emergencia", sa.Boolean(), nullable=False),
        sa.Column("hospitalizacion_emergencia_texto", sa.String(length=300), nullable=True),
        sa.Column("infecciones_frecuentes", sa.Boolean(), nullable=False),
        sa.Column("infecciones_frecuentes_zona", sa.String(length=200), nullable=True),
        sa.Column("tiempo_evolucion", sa.String(length=200), nullable=True),
        sa.Column("diseases", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("origin", sa.String(length=15), nullable=False),
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
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["annulled_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "systems_review_entries",
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("encounter_id", sa.UUID(), nullable=False),
        sa.Column("hematologico", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cardiovascular", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("neurologico", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("endocrino", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("respiratorio", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("genitourinario", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reproductor_masculino", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reproductor_femenino", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("origin", sa.String(length=15), nullable=False),
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
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["annulled_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column(
        "vital_signs", sa.Column("height_m", sa.Numeric(precision=3, scale=2), nullable=True)
    )
    op.add_column(
        "vital_signs", sa.Column("weight_kg", sa.Numeric(precision=5, scale=2), nullable=True)
    )
    op.add_column("vital_signs", sa.Column("spo2", sa.SmallInteger(), nullable=True))
    op.add_column(
        "vital_signs", sa.Column("glucose_index", sa.Numeric(precision=5, scale=1), nullable=True)
    )
    op.add_column("vital_signs", sa.Column("glucose_timing", sa.String(length=15), nullable=True))
    op.add_column("vital_signs", sa.Column("patient_attitude", sa.String(length=20), nullable=True))
    op.add_column(
        "vital_signs", sa.Column("asa_classification", sa.String(length=10), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("vital_signs", "asa_classification")
    op.drop_column("vital_signs", "patient_attitude")
    op.drop_column("vital_signs", "glucose_timing")
    op.drop_column("vital_signs", "glucose_index")
    op.drop_column("vital_signs", "spo2")
    op.drop_column("vital_signs", "weight_kg")
    op.drop_column("vital_signs", "height_m")
    op.drop_table("systems_review_entries")
    op.drop_table("personal_pathological_histories")
    op.drop_table("personal_non_pathological_histories")
    op.drop_table("family_history_entries")
