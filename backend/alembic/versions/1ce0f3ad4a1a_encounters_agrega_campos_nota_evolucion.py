"""encounters: agrega campos de la nota de evolucion a clinical_notes

Revision ID: 1ce0f3ad4a1a
Revises: 2aa4a3a3aeea
Create Date: 2026-10-27 00:05:00.000000

Fase D (docs/clinica/nota_evolucion.pdf): columnas nuevas y NULLABLE en
`clinical_notes` -- complementan el SOAP existente (soap_s/o/a/p/free_text),
no lo reemplazan. No se toca la maquina de estados DRAFT/FINAL/CORRECTED/
CANCELLED (regla 1 de CLAUDE.md): si la nota ya es FINAL, estos campos nuevos
se editan por el mismo flujo de correccion (POST /notes/{id}/correct) que ya
existe para soap_s/o/a/p, ver encounters/service.py.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "1ce0f3ad4a1a"
down_revision: str | None = "2aa4a3a3aeea"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_TEXT_COLUMNS = (
    "interrogatorio",
    "medicamentos",
    "estudios_radiograficos",
    "descripcion_procedimiento",
    "pronostico_evolucion",
    "indicaciones",
    "plan_proxima_cita",
    "evaluacion_actualizacion",
)


def upgrade() -> None:
    for column_name in _NEW_TEXT_COLUMNS:
        op.add_column("clinical_notes", sa.Column(column_name, sa.Text(), nullable=True))
    # Texto libre (no se exige formato de fecha estricto: el formato original
    # solo pide "Fecha de proxima cita", a veces se anota de forma relativa,
    # p.ej. "en 2 semanas").
    op.add_column(
        "clinical_notes", sa.Column("fecha_proxima_cita", sa.String(length=100), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("clinical_notes", "fecha_proxima_cita")
    for column_name in reversed(_NEW_TEXT_COLUMNS):
        op.drop_column("clinical_notes", column_name)
