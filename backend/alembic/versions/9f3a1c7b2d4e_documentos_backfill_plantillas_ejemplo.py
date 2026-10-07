"""documents: backfill de plantillas de ejemplo por sucursal

Revision ID: 9f3a1c7b2d4e
Revises: 6c4c973f6c89
Create Date: 2026-10-06 00:10:00.000000

Correccion A6 (docs/06_INSTRUCCIONES...): sin ninguna plantilla sembrada, el selector
de "Firmar y generar PDF" quedaba vacio y el flujo nunca se podia completar. Para cada
sucursal que todavia no tenga una plantilla vigente (is_current) de alguno de los 4
codigos del catalogo (general, extraccion, endodoncia, anestesia), se inserta una de
ejemplo -- marcada "Ejemplo - validar con la clinica" en el nombre porque el texto
legal real lo debe redactar/validar la clinica (docs/PENDIENTES_CLINICOS.md). Nunca
toca una plantilla que ya exista.
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9f3a1c7b2d4e"
down_revision: str | None = "6c4c973f6c89"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Misma redaccion que app/seed.py::DOCUMENT_TEMPLATE_SEEDS -- duplicada a proposito
# (convencion de este proyecto para migraciones de datos, ver
# e4823992f9d7_iam_agrega_permisos_diagnosis_read_y_.py): una migracion no debe
# depender del codigo de la aplicacion, que puede cambiar despues sin tocar el pasado.
TEMPLATE_SEEDS: list[tuple[str, str, str]] = [
    (
        "general",
        "Ejemplo — validar con la clinica: consentimiento general",
        "<p>Yo, {{paciente.nombre}}, de {{paciente.edad}} anos, autorizo a "
        "{{clinica.nombre}} y al profesional {{profesional.nombre}} a realizar el "
        "tratamiento dental que se me explico, incluidos sus riesgos y alternativas. "
        "Fecha: {{fecha}}.</p>",
    ),
    (
        "extraccion",
        "Ejemplo — validar con la clinica: extraccion dental",
        "<p>Autorizo a {{profesional.nombre}} a realizar la extraccion de la pieza "
        "indicada en mi expediente. Entiendo los riesgos (sangrado, infeccion, dano a "
        "piezas vecinas) y las alternativas de tratamiento. Procedimiento: "
        "{{procedimiento.nombre}}. Fecha: {{fecha}}.</p>",
    ),
    (
        "endodoncia",
        "Ejemplo — validar con la clinica: endodoncia (tratamiento de conductos)",
        "<p>Autorizo a {{profesional.nombre}} a realizar el tratamiento de conductos "
        "(endodoncia) indicado en mi plan de tratamiento "
        "{{plan.titulo}}. Entiendo que puede requerir mas de una cita y que existe "
        "riesgo de fractura o perdida de la pieza. Fecha: {{fecha}}.</p>",
    ),
    (
        "anestesia",
        "Ejemplo — validar con la clinica: anestesia local",
        "<p>Autorizo la aplicacion de anestesia local para mi tratamiento en "
        "{{clinica.nombre}}. He informado al profesional {{profesional.nombre}} de "
        "mis alergias y antecedentes medicos conocidos. Fecha: {{fecha}}.</p>",
    ),
]

clinics_table = sa.table("clinics", sa.column("id", sa.UUID()))
templates_table = sa.table(
    "document_templates",
    sa.column("id", sa.UUID()),
    sa.column("clinic_id", sa.UUID()),
    sa.column("code", sa.String()),
    sa.column("name", sa.String()),
    sa.column("version", sa.Integer()),
    sa.column("html_content", sa.Text()),
    sa.column("is_current", sa.Boolean()),
)


def upgrade() -> None:
    conn = op.get_bind()

    clinic_ids = [row.id for row in conn.execute(sa.select(clinics_table.c.id))]
    existing_codes_by_clinic: dict = {}
    for row in conn.execute(
        sa.select(templates_table.c.clinic_id, templates_table.c.code).where(
            templates_table.c.is_current.is_(True)
        )
    ):
        existing_codes_by_clinic.setdefault(row.clinic_id, set()).add(row.code)

    rows_to_insert = []
    for clinic_id in clinic_ids:
        existing_codes = existing_codes_by_clinic.get(clinic_id, set())
        for code, name, html_content in TEMPLATE_SEEDS:
            if code in existing_codes:
                continue
            rows_to_insert.append(
                {
                    "id": uuid.uuid4(),
                    "clinic_id": clinic_id,
                    "code": code,
                    "name": name,
                    "version": 1,
                    "html_content": html_content,
                    "is_current": True,
                }
            )

    if rows_to_insert:
        op.bulk_insert(templates_table, rows_to_insert)


def downgrade() -> None:
    # No reversible de forma segura: no hay como distinguir una plantilla de ejemplo
    # creada por esta migracion de una creada despues a mano con el mismo codigo.
    pass
