"""Cuenta de demostracion publica, de tiempo limitado (a peticion del operador).

Uso: python -m app.seed_demo

Crea (una sola vez; idempotente) una organizacion y sucursal propias, mas el
usuario `demo@prueba.com` con el rol "demo" (todos los permisos del catalogo,
ver permissions_catalog.py). Se activa el 26 de octubre de 2026 y queda
bloqueado para siempre despues del 29 (`User.expires_at`, revisado en cada
intento de login -- ver app/modules/iam/service.py).

Deliberadamente NO se llama desde `app/seed.py` ni desde el arranque de la
aplicacion: esta cuenta nunca debe poder crearse por accidente en
`dentia-prod` (mismo criterio que ya aplica a `python -m app.seed`, ver
docs/USUARIOS_Y_ACCESOS.md y docs/PENDIENTES_VPS.md) -- hay que correr este
script a proposito, una vez, en cada ambiente donde se quiera ofrecer esta
cuenta (localhost y demo.dentia.digital, nunca produccion).

El contenido clinico de esta sucursal (pacientes, citas, consentimientos...)
se reinicia solo en cada login/logout de `demo@prueba.com`
(app/modules/iam/demo_sandbox.py::reset_demo_clinic) -- este script solo
crea el usuario y la sucursal una vez; no hace falta volver a correrlo.
"""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session_factory
from app.core.security import hash_password
from app.modules.iam.models import Clinic, Organization, Role, User, UserClinic

DEMO_EMAIL = "demo@prueba.com"
DEMO_PASSWORD = "Demo@1234prueba"
DEMO_FULL_NAME = "Cuenta de demostracion"
# Ventana activa pedida por el operador: 26-29 de octubre de 2026 inclusive.
# Hora de corte fija en UTC (no depende de la zona horaria de la sucursal,
# a diferencia de "hoy" en la agenda -- esto es un limite administrativo).
DEMO_EXPIRES_AT = datetime(2026, 10, 30, 5, 59, 59, tzinfo=UTC)


async def ensure_demo_account(db: AsyncSession) -> tuple[User, Clinic]:
    existing = (await db.execute(select(User).where(User.email == DEMO_EMAIL))).scalar_one_or_none()
    if existing is not None:
        clinic_id = (
            await db.execute(select(UserClinic.clinic_id).where(UserClinic.user_id == existing.id))
        ).scalar_one()
        clinic = await db.get(Clinic, clinic_id)
        assert clinic is not None
        return existing, clinic

    organization = Organization(name="Demostracion publica")
    db.add(organization)
    await db.flush()

    clinic = Clinic(
        organization_id=organization.id,
        name="Clinica de demostracion",
        address="N/A",
        phone="N/A",
    )
    db.add(clinic)
    await db.flush()

    demo_role = (await db.execute(select(Role).where(Role.code == "demo"))).scalar_one()

    user = User(
        email=DEMO_EMAIL,
        full_name=DEMO_FULL_NAME,
        professional_license="DEMO0000000",
        hashed_password=hash_password(DEMO_PASSWORD),
        is_sandboxed=True,
        expires_at=DEMO_EXPIRES_AT,
    )
    db.add(user)
    await db.flush()

    db.add(UserClinic(user_id=user.id, clinic_id=clinic.id, role_id=demo_role.id))
    await db.commit()
    return user, clinic


async def main() -> None:
    async with async_session_factory() as db:
        user, clinic = await ensure_demo_account(db)
        print(f"Cuenta de demostracion: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print(f"Activa hasta (UTC): {DEMO_EXPIRES_AT}")
        print(f"Sucursal dedicada: {clinic.name} ({clinic.id})")
        print(
            "El contenido clinico de esa sucursal se reinicia solo en cada "
            "login/logout -- no hace falta volver a correr este script."
        )


if __name__ == "__main__":
    asyncio.run(main())
