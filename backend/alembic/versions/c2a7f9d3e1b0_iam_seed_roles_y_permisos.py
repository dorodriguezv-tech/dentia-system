"""iam: seed de roles y permisos (CLAUDE.md sec. 5)

Revision ID: c2a7f9d3e1b0
Revises: b6c1e0a5f4ac
Create Date: 2026-10-04 19:05:00.000000

Los diccionarios de abajo son una copia congelada de
app/modules/iam/permissions_catalog.py tal como estaba en esta fecha -- NO se
importa el modulo en vivo (mismo motivo que e4823992f9d7 y 4d7a2e9c15f3: una
migracion no debe depender del codigo de la aplicacion, que sigue cambiando
despues sin tocar el pasado). Los permisos agregados mas tarde por su propia
migracion incremental (diagnosis.read/treatment.read en e4823992f9d7,
billing.configure en a1c3e7f90b22, catalogs.manage en 4d7a2e9c15f3,
voice.use/voice.clinical en 88aa5ab01296) se excluyen aqui a proposito: de lo
contrario esta migracion los insertaria primero y la migracion incremental
fallaria con "ya existe" al correr sobre una base de datos nueva.
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c2a7f9d3e1b0"
down_revision: str | None = "b6c1e0a5f4ac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLES: dict[str, str] = {
    "superadmin": "Super administrador",
    "admin_clinica": "Administrador de la clinica",
    "odontologo": "Odontologo",
    "especialista": "Especialista",
    "asistente": "Asistente dental",
    "recepcion": "Recepcion",
    "caja": "Caja",
}

PERMISSIONS: dict[str, str] = {
    "iam.manage_organizations": "Crear y administrar organizaciones",
    "iam.manage_clinics": "Crear y administrar sucursales",
    "iam.manage_users": "Crear, editar y asignar roles a usuarios de la clinica",
    "iam.view_users": "Ver usuarios de la clinica",
    "audit.read": "Consultar la bitacora de auditoria",
    "branding.manage": "Editar nombre, logo y colores de la clinica",
    "patients.read": "Ver pacientes",
    "patients.write": "Crear y editar pacientes",
    "records.read": "Ver el expediente clinico",
    "records.write": "Editar el expediente clinico",
    "odontogram.read": "Ver el odontograma",
    "odontogram.write": "Editar el odontograma",
    "agenda.read": "Ver la agenda",
    "agenda.write": "Crear y modificar citas",
    "diagnosis.write": "Registrar diagnosticos",
    "treatment.write": "Crear planes de tratamiento",
    "treatment.accept_budget": "Aceptar o rechazar presupuestos",
    "documents.read": "Ver documentos y consentimientos",
    "documents.write": "Generar documentos y consentimientos",
    "documents.sign": "Firmar consentimientos",
    "imaging.read": "Ver imagenes y radiografias",
    "imaging.write": "Cargar imagenes y radiografias",
    "billing.read": "Ver cargos, pagos y saldos",
    "billing.write": "Registrar cargos y pagos",
    "reports.read": "Ver reportes",
    "ai.use": "Usar el asistente de IA por voz",
    "ai.configure": "Configurar el asistente de IA",
}

ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "superadmin": (
        "iam.manage_organizations",
        "iam.manage_clinics",
        "iam.manage_users",
        "iam.view_users",
        "audit.read",
        "branding.manage",
        "reports.read",
    ),
    "admin_clinica": (
        "iam.manage_users",
        "iam.view_users",
        "audit.read",
        "branding.manage",
        "patients.read",
        "patients.write",
        "agenda.read",
        "agenda.write",
        "billing.read",
        "billing.write",
        "documents.read",
        "reports.read",
        "ai.configure",
    ),
    "odontologo": (
        "patients.read",
        "records.read",
        "records.write",
        "odontogram.read",
        "odontogram.write",
        "diagnosis.write",
        "treatment.write",
        "treatment.accept_budget",
        "documents.read",
        "documents.write",
        "documents.sign",
        "imaging.read",
        "imaging.write",
        "agenda.read",
        "agenda.write",
        "ai.use",
    ),
    "especialista": (
        "patients.read",
        "records.read",
        "records.write",
        "odontogram.read",
        "odontogram.write",
        "diagnosis.write",
        "treatment.write",
        "treatment.accept_budget",
        "documents.read",
        "documents.write",
        "documents.sign",
        "imaging.read",
        "imaging.write",
        "agenda.read",
        "agenda.write",
        "ai.use",
    ),
    "asistente": (
        "patients.read",
        "odontogram.read",
        "imaging.read",
        "imaging.write",
        "agenda.read",
    ),
    "recepcion": (
        "patients.read",
        "patients.write",
        "agenda.read",
        "agenda.write",
        "billing.read",
    ),
    "caja": (
        "patients.read",
        "billing.read",
        "billing.write",
        "reports.read",
    ),
}

roles_table = sa.table(
    "roles",
    sa.column("id", sa.UUID()),
    sa.column("code", sa.String()),
    sa.column("name", sa.String()),
)
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


def upgrade() -> None:
    role_ids = {code: uuid.uuid4() for code in ROLES}
    permission_ids = {code: uuid.uuid4() for code in PERMISSIONS}

    op.bulk_insert(
        roles_table,
        [{"id": role_ids[code], "code": code, "name": name} for code, name in ROLES.items()],
    )
    op.bulk_insert(
        permissions_table,
        [
            {"id": permission_ids[code], "code": code, "description": description}
            for code, description in PERMISSIONS.items()
        ],
    )
    op.bulk_insert(
        role_permissions_table,
        [
            {"role_id": role_ids[role_code], "permission_id": permission_ids[permission_code]}
            for role_code, codes in ROLE_PERMISSIONS.items()
            for permission_code in codes
        ],
    )


def downgrade() -> None:
    op.execute(sa.delete(role_permissions_table))
    op.execute(sa.delete(permissions_table))
    op.execute(sa.delete(roles_table))
