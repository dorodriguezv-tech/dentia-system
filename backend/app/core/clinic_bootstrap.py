"""Helpers compartidos por los comandos de alta controlada (app.bootstrap_clinic,
app.create_admin): obtener o crear la Organization/Clinic por nombre, sin
duplicar esta logica entre ambos scripts."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.iam.models import Clinic, Organization


async def get_or_create_organization(db: AsyncSession, *, name: str) -> Organization:
    existing = (
        await db.execute(select(Organization).where(Organization.name == name))
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    organization = Organization(name=name)
    db.add(organization)
    await db.flush()
    return organization


async def get_or_create_clinic(
    db: AsyncSession, *, organization: Organization, name: str
) -> Clinic:
    existing = (
        await db.execute(
            select(Clinic).where(Clinic.organization_id == organization.id, Clinic.name == name)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    clinic = Clinic(organization_id=organization.id, name=name)
    db.add(clinic)
    await db.flush()
    return clinic
