"""Datos ficticios de arranque (CLAUDE.md sec. 5: nunca datos reales de pacientes).

Uso: python -m app.seed
Crea una organizacion y una sucursal de ejemplo, un admin_clinica (con MFA
pendiente de configurar, ver regla de CLAUDE.md sec. 5) y un odontologo.
Es idempotente: si el admin ya existe, no hace nada.
"""

import asyncio
import random
import uuid

from faker import Faker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_factory
from app.core.security import hash_password
from app.modules.iam.models import Clinic, Organization, Role, User, UserClinic
from app.modules.patients import service as patients_service
from app.modules.patients.schemas import PatientCreateRequest

fake = Faker("es_MX")

ADMIN_EMAIL = "admin@dentalcare-demo.mx"
ODONTOLOGO_EMAIL = "odontologo@dentalcare-demo.mx"
DEMO_PASSWORD = "Dentia2025!"
PATIENT_COUNT = 50


async def _seed_patients(db: AsyncSession, *, clinic_id: uuid.UUID, actor_id: uuid.UUID) -> None:
    for _ in range(PATIENT_COUNT):
        data = PatientCreateRequest(
            first_name=fake.first_name(),
            last_name_paternal=fake.last_name(),
            last_name_maternal=fake.last_name(),
            date_of_birth=fake.date_of_birth(minimum_age=1, maximum_age=90),
            sex=random.choice(["F", "M", None]),
            phone=fake.phone_number(),
            email=fake.unique.email(),
            address=fake.address().replace("\n", ", "),
        )
        await patients_service.create_patient(db, clinic_id=clinic_id, data=data, actor_id=actor_id)


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

        await _seed_patients(db, clinic_id=clinic.id, actor_id=admin.id)

        print(f"Organizacion: {organization.name}")
        print(f"Sucursal: {clinic.name}")
        print(f"Admin: {ADMIN_EMAIL} / {DEMO_PASSWORD} (debe configurar MFA al entrar)")
        print(f"Odontologo: {ODONTOLOGO_EMAIL} / {DEMO_PASSWORD}")
        print(f"Pacientes ficticios creados: {PATIENT_COUNT}")


if __name__ == "__main__":
    asyncio.run(seed())
