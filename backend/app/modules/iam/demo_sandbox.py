"""Reinicia la sucursal de la cuenta de demostracion (`User.is_sandboxed`) a un
estado de ejemplo fijo, en cada login y cada logout -- a peticion del operador,
nada de lo que haga un visitante con esa cuenta debe sobrevivir a su sesion.

Mapa de tablas por `clinic_id` (y su orden seguro de borrado, respetando las
llaves foraneas RESTRICT/CASCADE de cada modulo) investigado a proposito para
esta funcion -- ver el historial de este archivo si hace falta revisarlo.
`audit_events` se deja fuera a proposito: un trigger de PostgreSQL bloquea su
DELETE por completo (ver app/audit/models.py), y de cualquier forma es
auditoria, no contenido clinico que deba "resetearse".

Lo que se conserva entre reinicios (nunca se borra, solo se siembra una vez):
catalogos de la sucursal, plantillas de documentos, catalogo de
procedimientos, el Provider/Resource de la propia cuenta y su membresia
(`user_clinics`) -- son configuracion, no contenido de pacientes.
"""

import uuid
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agenda import service as agenda_service
from app.modules.agenda.models import Provider, Resource
from app.modules.agenda.schemas import ProviderCreateRequest, ResourceCreateRequest
from app.modules.catalogs.models import ClinicCatalogItem
from app.modules.documents.models import DocumentTemplate
from app.modules.treatment import service as treatment_service
from app.modules.treatment.models import ProcedureCatalog
from app.modules.treatment.schemas import ProcedureCatalogCreateRequest

# Orden de borrado: hijos antes que padres (ver docstring del modulo).
_WIPE_TABLES_IN_ORDER = (
    "ai_suggestions",
    "images",
    "consents",
    "procedures_performed",
    "procedures_planned",
    "treatment_plans",
    "diagnoses",
    "tooth_findings",
    "medical_history",
    "allergies",
    "medications",
    "vital_signs",
    "payments",
    "cash_sessions",
    "appointments",
    "waitlist_entries",
    "encounters",
    "patients",
    "voice_command_logs",
)

# Mismo catalogo de procedimientos que usa el seed general (app/seed.py,
# _seed_treatment) -- duplicado a proposito, esta sucursal no depende del
# resto del seed para existir.
_PROCEDURE_CATALOG_SEEDS: tuple[tuple[str, str, str], ...] = (
    ("consulta_valoracion", "Consulta de valoracion", "300.00"),
    ("resina_oclusal", "Resina oclusal", "650.00"),
    ("limpieza_dental", "Limpieza dental (profilaxis)", "450.00"),
    ("endodoncia_unirradicular", "Endodoncia unirradicular", "2800.00"),
    ("corona_metal_porcelana", "Corona metal-porcelana", "4500.00"),
)


async def _ensure_provider_and_resource(
    db: AsyncSession, *, clinic_id: uuid.UUID, demo_user_id: uuid.UUID
) -> tuple[Provider, Resource]:
    provider = (
        await db.execute(select(Provider).where(Provider.clinic_id == clinic_id))
    ).scalar_one_or_none()
    if provider is None:
        provider, _name = await agenda_service.create_provider(
            db,
            clinic_id=clinic_id,
            data=ProviderCreateRequest(user_id=demo_user_id, color="#2BB3A3"),
            actor_id=demo_user_id,
        )

    resource = (
        await db.execute(select(Resource).where(Resource.clinic_id == clinic_id))
    ).scalar_one_or_none()
    if resource is None:
        resource = await agenda_service.create_resource(
            db,
            clinic_id=clinic_id,
            data=ResourceCreateRequest(name="Consultorio de demostracion"),
            actor_id=demo_user_id,
        )
    return provider, resource


async def _ensure_baseline_catalogs(
    db: AsyncSession, *, clinic_id: uuid.UUID, demo_user_id: uuid.UUID
) -> None:
    # Import diferido: evita un ciclo de import (app.seed importa de varios
    # modulos de app.modules.*; este modulo vive dentro de app.modules.iam).
    from app.seed import _seed_catalogs, _seed_document_templates

    has_catalog = (
        await db.execute(select(ClinicCatalogItem).where(ClinicCatalogItem.clinic_id == clinic_id))
    ).first()
    if has_catalog is None:
        await _seed_catalogs(db, clinic_id=clinic_id, actor_id=demo_user_id)

    has_templates = (
        await db.execute(select(DocumentTemplate).where(DocumentTemplate.clinic_id == clinic_id))
    ).first()
    if has_templates is None:
        await _seed_document_templates(db, clinic_id=clinic_id, actor_id=demo_user_id)

    has_procedures = (
        await db.execute(select(ProcedureCatalog).where(ProcedureCatalog.clinic_id == clinic_id))
    ).first()
    if has_procedures is None:
        for code, name, price in _PROCEDURE_CATALOG_SEEDS:
            await treatment_service.create_procedure_catalog_item(
                db,
                clinic_id=clinic_id,
                data=ProcedureCatalogCreateRequest(
                    code=code, name=name, default_price=Decimal(price)
                ),
                actor_id=demo_user_id,
            )


async def reset_demo_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, demo_user_id: uuid.UUID
) -> None:
    """Borra todo el contenido clinico de `clinic_id` y vuelve a sembrar un
    paciente de ejemplo completo. Pensada para llamarse en cada login/logout
    de la cuenta de demostracion -- nunca para una sucursal real."""
    for table in _WIPE_TABLES_IN_ORDER:
        await db.execute(
            text(f"DELETE FROM {table} WHERE clinic_id = :clinic_id"),  # noqa: S608
            {"clinic_id": clinic_id},
        )
    await db.commit()
    # El DELETE crudo de arriba no pasa por el ORM: sin esto, objetos de una
    # consulta anterior en esta misma sesion podrian quedar "vivos" en el mapa
    # de identidad apuntando a filas que ya no existen.
    db.expire_all()

    provider, resource = await _ensure_provider_and_resource(
        db, clinic_id=clinic_id, demo_user_id=demo_user_id
    )
    await _ensure_baseline_catalogs(db, clinic_id=clinic_id, demo_user_id=demo_user_id)

    # Import diferido, mismo motivo que arriba.
    from app.seed import _seed_example_patient

    await _seed_example_patient(
        db,
        clinic_id=clinic_id,
        admin_id=demo_user_id,
        professional_id=demo_user_id,
        provider_id=provider.id,
        resource_id=resource.id,
    )
