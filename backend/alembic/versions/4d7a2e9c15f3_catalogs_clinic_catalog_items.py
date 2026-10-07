"""catalogs: clinic_catalog_items, permiso catalogs.manage y backfill desde las
constantes fijas (Fase 12.2, Parte B1)

Revision ID: 4d7a2e9c15f3
Revises: 2b8e5f6a1c90
Create Date: 2026-10-06 00:30:00.000000

Antes de esta fase, "Tipos de consulta/cita" (agenda/rules.py), "Hallazgos del
odontograma" (odontogram/finding_catalog.py), "Diagnosticos" (diagnosis/rules.py),
"Categorias de antecedentes" y "Palabras clave de alerta" (records/rules.py) vivian
fijos en codigo: el administrador no podia agregar ni desactivar un elemento sin
pedir un cambio de codigo. Esta migracion crea la tabla, el permiso nuevo
(`catalogs.manage`, solo `admin_clinica`) y siembra los mismos valores que ya
estaban en codigo para cada sucursal existente -- los valores quedan duplicados
aqui a proposito (convencion de este proyecto para migraciones de datos, ver
e4823992f9d7_iam_agrega_permisos_diagnosis_read_y_.py): una migracion no debe
depender del codigo de la aplicacion, que puede cambiar despues sin tocar el
pasado. "Metodos de pago", "Procedimientos y precios" (ya es su propia tabla,
`procedure_catalog`) y "Gabinetes"/"Sucursales" (ya son tablas propias,
`resources`/`clinics`) se dejan fuera (ver app/modules/catalogs/rules.py).
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "4d7a2e9c15f3"
down_revision: str | None = "2b8e5f6a1c90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_PERMISSION_CODE = "catalogs.manage"
NEW_PERMISSION_DESCRIPTION = (
    "Administrar catalogos de la clinica (tipos de cita, hallazgos, diagnosticos...)"
)
ROLE_CODE_WITH_ACCESS = "admin_clinica"

# (catalog_type, code, name, sort_order, extra)
CATALOG_SEEDS: list[tuple[str, str, str, int, dict]] = [
    # agenda/rules.py::APPOINTMENT_TYPES
    ("appointment_type", "consulta", "Consulta / valoracion", 0, {"default_minutes": 30}),
    ("appointment_type", "limpieza", "Limpieza dental", 1, {"default_minutes": 45}),
    (
        "appointment_type",
        "restauracion",
        "Restauracion (resina/amalgama)",
        2,
        {"default_minutes": 60},
    ),
    ("appointment_type", "endodoncia", "Endodoncia", 3, {"default_minutes": 90}),
    ("appointment_type", "extraccion", "Extraccion", 4, {"default_minutes": 45}),
    (
        "appointment_type",
        "ortodoncia_control",
        "Control de ortodoncia",
        5,
        {"default_minutes": 20},
    ),
    ("appointment_type", "protesis", "Protesis", 6, {"default_minutes": 60}),
    ("appointment_type", "urgencia", "Urgencia", 7, {"default_minutes": 30}),
    # odontogram/finding_catalog.py::FINDING_CATALOG -- "requires_surface" es nuevo
    # (antes la superficie siempre era opcional sin importar el hallazgo): valor por
    # defecto razonable segun si el hallazgo tipicamente aplica a toda la pieza o no
    # (CLAUDE.md sec. 7, catalogo configurable -- ver docs/PENDIENTES_CLINICOS.md).
    (
        "odontogram_finding",
        "sano",
        "Sano",
        0,
        {"color": "#A9C6B8", "symbol": "", "requires_surface": True},
    ),
    (
        "odontogram_finding",
        "caries",
        "Caries",
        1,
        {"color": "#D64545", "symbol": "C", "requires_surface": True},
    ),
    (
        "odontogram_finding",
        "restauracion",
        "Restauracion",
        2,
        {"color": "#4A90C2", "symbol": "R", "requires_surface": True},
    ),
    (
        "odontogram_finding",
        "corona",
        "Corona",
        3,
        {"color": "#E0A100", "symbol": "CO", "requires_surface": False},
    ),
    (
        "odontogram_finding",
        "endodoncia",
        "Endodoncia",
        4,
        {"color": "#7B5EA7", "symbol": "E", "requires_surface": False},
    ),
    (
        "odontogram_finding",
        "ausente",
        "Ausente",
        5,
        {"color": "#8C8C8C", "symbol": "X", "requires_surface": False},
    ),
    (
        "odontogram_finding",
        "extraccion_indicada",
        "Extraccion indicada",
        6,
        {"color": "#D64545", "symbol": "XI", "requires_surface": False},
    ),
    (
        "odontogram_finding",
        "implante",
        "Implante",
        7,
        {"color": "#2BB3A3", "symbol": "IM", "requires_surface": False},
    ),
    (
        "odontogram_finding",
        "protesis_fija",
        "Protesis fija",
        8,
        {"color": "#3A7FC1", "symbol": "PF", "requires_surface": False},
    ),
    (
        "odontogram_finding",
        "sellador",
        "Sellador",
        9,
        {"color": "#6AB04C", "symbol": "S", "requires_surface": True},
    ),
    (
        "odontogram_finding",
        "fractura",
        "Fractura",
        10,
        {"color": "#B8460E", "symbol": "FX", "requires_surface": True},
    ),
    (
        "odontogram_finding",
        "movilidad",
        "Movilidad",
        11,
        {"color": "#C77D1E", "symbol": "MO", "requires_surface": False},
    ),
    # diagnosis/rules.py::DIAGNOSIS_CATALOG
    ("diagnosis", "caries", "Caries dental", 0, {}),
    ("diagnosis", "caries_recurrente", "Caries recurrente", 1, {}),
    ("diagnosis", "pulpitis_reversible", "Pulpitis reversible", 2, {}),
    ("diagnosis", "pulpitis_irreversible", "Pulpitis irreversible", 3, {}),
    ("diagnosis", "necrosis_pulpar", "Necrosis pulpar", 4, {}),
    ("diagnosis", "absceso_periapical", "Absceso periapical", 5, {}),
    ("diagnosis", "gingivitis", "Gingivitis", 6, {}),
    ("diagnosis", "periodontitis", "Periodontitis", 7, {}),
    ("diagnosis", "fractura_dental", "Fractura dental", 8, {}),
    ("diagnosis", "edentulismo_parcial", "Edentulismo parcial", 9, {}),
    ("diagnosis", "maloclusion", "Maloclusion", 10, {}),
    ("diagnosis", "sin_hallazgos", "Sin hallazgos patologicos", 11, {}),
    # records/rules.py::HISTORY_CATEGORIES (+ frontend/.../records/types.ts
    # HISTORY_CATEGORY_LABELS, unica fuente de las etiquetas hasta ahora)
    ("history_category", "heredofamiliar", "Heredofamiliar", 0, {}),
    ("history_category", "personal_patologico", "Personal patologico", 1, {}),
    ("history_category", "personal_no_patologico", "Personal no patologico", 2, {}),
    ("history_category", "odontologico", "Odontologico", 3, {}),
    ("history_category", "habito", "Habito", 4, {}),
    ("history_category", "factor_riesgo", "Factor de riesgo", 5, {}),
    # records/rules.py::CONDITION_ALERT_KEYWORDS
    (
        "condition_alert_keyword",
        "diabetes",
        "diabetes",
        0,
        {"alert_label": "Paciente con diabetes"},
    ),
    (
        "condition_alert_keyword",
        "embarazo",
        "embarazo",
        1,
        {"alert_label": "Paciente embarazada"},
    ),
    (
        "condition_alert_keyword",
        "embarazada",
        "embarazada",
        2,
        {"alert_label": "Paciente embarazada"},
    ),
    (
        "condition_alert_keyword",
        "hipertension",
        "hipertension",
        3,
        {"alert_label": "Paciente hipertenso"},
    ),
    (
        "condition_alert_keyword",
        "marcapasos",
        "marcapasos",
        4,
        {"alert_label": "Paciente con marcapasos"},
    ),
    (
        "condition_alert_keyword",
        "hemofilia",
        "hemofilia",
        5,
        {"alert_label": "Paciente con trastorno de coagulacion"},
    ),
    ("condition_alert_keyword", "vih", "vih", 6, {"alert_label": "Paciente con VIH"}),
    (
        "condition_alert_keyword",
        "hepatitis",
        "hepatitis",
        7,
        {"alert_label": "Paciente con hepatitis"},
    ),
    (
        "condition_alert_keyword",
        "epilepsia",
        "epilepsia",
        8,
        {"alert_label": "Paciente con epilepsia"},
    ),
    (
        "condition_alert_keyword",
        "cardiopatia",
        "cardiopatia",
        9,
        {"alert_label": "Paciente con cardiopatia"},
    ),
    # records/rules.py::MEDICATION_ALERT_KEYWORDS
    (
        "medication_alert_keyword",
        "anticoagulante",
        "anticoagulante",
        0,
        {"alert_label": "Paciente usa anticoagulantes"},
    ),
    (
        "medication_alert_keyword",
        "warfarina",
        "warfarina",
        1,
        {"alert_label": "Paciente usa anticoagulantes (warfarina)"},
    ),
    (
        "medication_alert_keyword",
        "acenocumarina",
        "acenocumarina",
        2,
        {"alert_label": "Paciente usa anticoagulantes (acenocumarina)"},
    ),
    (
        "medication_alert_keyword",
        "rivaroxaban",
        "rivaroxaban",
        3,
        {"alert_label": "Paciente usa anticoagulantes (rivaroxaban)"},
    ),
    (
        "medication_alert_keyword",
        "apixaban",
        "apixaban",
        4,
        {"alert_label": "Paciente usa anticoagulantes (apixaban)"},
    ),
    (
        "medication_alert_keyword",
        "clopidogrel",
        "clopidogrel",
        5,
        {"alert_label": "Paciente usa antiagregantes plaquetarios (clopidogrel)"},
    ),
    (
        "medication_alert_keyword",
        "aspirina",
        "aspirina",
        6,
        {"alert_label": "Paciente usa antiagregantes plaquetarios (aspirina)"},
    ),
    (
        "medication_alert_keyword",
        "insulina",
        "insulina",
        7,
        {"alert_label": "Paciente usa insulina"},
    ),
    (
        "medication_alert_keyword",
        "bifosfonato",
        "bifosfonato",
        8,
        {"alert_label": "Paciente usa bifosfonatos (riesgo de osteonecrosis)"},
    ),
    (
        "medication_alert_keyword",
        "corticoesteroide",
        "corticoesteroide",
        9,
        {"alert_label": "Paciente usa corticoesteroides"},
    ),
    (
        "medication_alert_keyword",
        "inmunosupresor",
        "inmunosupresor",
        10,
        {"alert_label": "Paciente usa inmunosupresores"},
    ),
]

clinics_table = sa.table("clinics", sa.column("id", sa.UUID()))
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
catalog_items_table = sa.table(
    "clinic_catalog_items",
    sa.column("id", sa.UUID()),
    sa.column("clinic_id", sa.UUID()),
    sa.column("catalog_type", sa.String()),
    sa.column("code", sa.String()),
    sa.column("name", sa.String()),
    sa.column("is_active", sa.Boolean()),
    sa.column("sort_order", sa.Integer()),
    sa.column("extra", postgresql.JSONB()),
)


def upgrade() -> None:
    op.create_table(
        "clinic_catalog_items",
        sa.Column("clinic_id", sa.UUID(), nullable=False),
        sa.Column("catalog_type", sa.String(length=40), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("clinic_id", "catalog_type", "code", name="uq_catalog_item_code"),
    )
    op.create_index(
        "ix_clinic_catalog_items_clinic_id", "clinic_catalog_items", ["clinic_id"]
    )
    op.create_index(
        "ix_clinic_catalog_items_catalog_type", "clinic_catalog_items", ["catalog_type"]
    )

    conn = op.get_bind()

    permission_id = uuid.uuid4()
    op.bulk_insert(
        permissions_table,
        [{"id": permission_id, "code": NEW_PERMISSION_CODE, "description": NEW_PERMISSION_DESCRIPTION}],
    )
    role_id = conn.execute(
        sa.select(roles_table.c.id).where(roles_table.c.code == ROLE_CODE_WITH_ACCESS)
    ).scalar_one()
    op.bulk_insert(
        role_permissions_table, [{"role_id": role_id, "permission_id": permission_id}]
    )

    clinic_ids = [row.id for row in conn.execute(sa.select(clinics_table.c.id))]
    rows_to_insert = [
        {
            "id": uuid.uuid4(),
            "clinic_id": clinic_id,
            "catalog_type": catalog_type,
            "code": code,
            "name": name,
            "is_active": True,
            "sort_order": sort_order,
            "extra": extra,
        }
        for clinic_id in clinic_ids
        for catalog_type, code, name, sort_order, extra in CATALOG_SEEDS
    ]
    if rows_to_insert:
        op.bulk_insert(catalog_items_table, rows_to_insert)


def downgrade() -> None:
    # role_permissions.permission_id tiene ON DELETE CASCADE: borrar el permiso
    # tambien borra su fila de role_permissions.
    op.execute(
        sa.delete(permissions_table).where(permissions_table.c.code == NEW_PERMISSION_CODE)
    )
    op.drop_index("ix_clinic_catalog_items_catalog_type", table_name="clinic_catalog_items")
    op.drop_index("ix_clinic_catalog_items_clinic_id", table_name="clinic_catalog_items")
    op.drop_table("clinic_catalog_items")
