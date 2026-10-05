"""Datos ficticios de arranque (CLAUDE.md sec. 5: nunca datos reales de pacientes).

Uso: python -m app.seed
Crea una organizacion y una sucursal de ejemplo, un admin_clinica (con MFA
pendiente de configurar, ver regla de CLAUDE.md sec. 5) y un odontologo.
Es idempotente: si el admin ya existe, no hace nada.
"""

import asyncio

from faker import Faker
from sqlalchemy import select

from app.core.db import async_session_factory
from app.core.security import hash_password
from app.modules.iam.models import Clinic, Organization, Role, User, UserClinic

fake = Faker("es_MX")

ADMIN_EMAIL = "admin@dentalcare-demo.mx"
ODONTOLOGO_EMAIL = "odontologo@dentalcare-demo.mx"
DEMO_PASSWORD = "Dentia2025!"


async def seed() -> None:
    async with async_session_factory() as db:
        existing = (
            await db.execute(select(User).where(User.email == ADMIN_EMAIL))
        ).scalar_one_or_none()
        if existing is not None:
            print("El seed ya se aplico antes; no se hace nada.")
            return

        organization = Organization(name="Clinica Dental Demo")
        db.add(organization)
        await db.flush()

        clinic = Clinic(
            organization_id=organization.id,
            name="Sucursal Centro",
            address=fake.address(),
            phone=fake.phone_number(),
        )
        db.add(clinic)
        await db.flush()

        admin_role = (
            await db.execute(select(Role).where(Role.code == "admin_clinica"))
        ).scalar_one()
        odontologo_role = (
            await db.execute(select(Role).where(Role.code == "odontologo"))
        ).scalar_one()

        admin = User(
            email=ADMIN_EMAIL,
            full_name=fake.name(),
            hashed_password=hash_password(DEMO_PASSWORD),
        )
        odontologo = User(
            email=ODONTOLOGO_EMAIL,
            full_name=fake.name(),
            hashed_password=hash_password(DEMO_PASSWORD),
        )
        db.add_all([admin, odontologo])
        await db.flush()

        db.add_all(
            [
                UserClinic(user_id=admin.id, clinic_id=clinic.id, role_id=admin_role.id),
                UserClinic(user_id=odontologo.id, clinic_id=clinic.id, role_id=odontologo_role.id),
            ]
        )
        await db.commit()

        print(f"Organizacion: {organization.name}")
        print(f"Sucursal: {clinic.name}")
        print(f"Admin: {ADMIN_EMAIL} / {DEMO_PASSWORD} (debe configurar MFA al entrar)")
        print(f"Odontologo: {ODONTOLOGO_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
