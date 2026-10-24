"""Alta controlada de la clinica y sus usuarios iniciales en produccion.

CLAUDE.md sec. 5 prohibe datos reales de paciente en los seeds (Faker es_MX);
este script es justo lo contrario de app.seed: no crea NADA ficticio (ni
pacientes, ni citas, ni historiales) -- solo la organizacion, la sucursal y
exactamente los usuarios reales que se le indiquen, con las credenciales que
de verdad va a usar el personal. Es idempotente: se puede volver a correr
(por ejemplo si fallo a la mitad) sin duplicar nada que ya exista.

Uso (PowerShell, backend\\.venv activado):

    $env:BOOTSTRAP_PASSWORD = "<contrasena-inicial>"
    python -m app.bootstrap_clinic --clinic-name "Clinica EMO" --email-domain clinica.emo
    Remove-Item Env:\\BOOTSTRAP_PASSWORD

La contrasena SOLO se lee de la variable de entorno BOOTSTRAP_PASSWORD (nunca
como argumento de linea de comandos ni con un valor por defecto en el codigo)
para que nunca quede un secreto real en el historial de git ni en este
archivo versionado -- ver docs/INSTALACION_PRODUCCION.md.

Crea exactamente 3 cuentas, una por rol (ver docs/MATRIZ_PERMISOS.md para lo
que cada rol puede hacer):

    agenda@<dominio>      -- recepcion     (agenda.write, patients.write)
    admin@<dominio>       -- admin_clinica (administracion de la clinica)
    odontologo@<dominio>  -- odontologo    (expediente, odontograma, notas)

Recomendacion fuerte: las 3 cuentas comparten la misma contrasena solo para
el arranque inicial -- cada persona debe cambiarla la primera vez que entra
(Mi perfil -> Cambiar contrasena) antes de usar el sistema con pacientes
reales.
"""

import argparse
import asyncio
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clinic_bootstrap import get_or_create_clinic, get_or_create_organization
from app.core.db import async_session_factory
from app.core.security import hash_password
from app.modules.iam.models import Role, User, UserClinic

# code de Role -> (prefijo del correo, nombre completo por defecto, editable
# despues desde Usuarios por admin_clinica).
_ACCOUNTS: list[tuple[str, str, str]] = [
    ("recepcion", "agenda", "Recepcion / Agenda"),
    ("admin_clinica", "admin", "Administrador de la clinica"),
    ("odontologo", "odontologo", "Odontologo"),
]


async def bootstrap(
    db: AsyncSession, *, clinic_name: str, email_domain: str, password: str, dry_run: bool = False
) -> tuple[list[str], list[str]]:
    """Logica pura, con la sesion inyectada (testeable con el fixture db_session).
    Devuelve (creados, existentes) como lista de correos."""
    organization = await get_or_create_organization(db, name=clinic_name)
    clinic = await get_or_create_clinic(db, organization=organization, name=clinic_name)

    hashed = hash_password(password)
    created: list[str] = []
    skipped: list[str] = []

    for role_code, local_part, default_full_name in _ACCOUNTS:
        email = f"{local_part}@{email_domain}"
        role = (await db.execute(select(Role).where(Role.code == role_code))).scalar_one()

        user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if user is not None:
            skipped.append(email)
            continue
        if dry_run:
            created.append(email)
            continue

        user = User(email=email, full_name=default_full_name, hashed_password=hashed)
        db.add(user)
        await db.flush()
        db.add(UserClinic(user_id=user.id, clinic_id=clinic.id, role_id=role.id))
        created.append(email)

    if dry_run:
        await db.rollback()
    else:
        await db.commit()
    return created, skipped


async def _run(*, clinic_name: str, email_domain: str, password: str, dry_run: bool) -> None:
    async with async_session_factory() as db:
        created, skipped = await bootstrap(
            db,
            clinic_name=clinic_name,
            email_domain=email_domain,
            password=password,
            dry_run=dry_run,
        )

        print(f"Organizacion/sucursal: {clinic_name}")
        if created:
            label = "Usuarios que se crearian:" if dry_run else "Usuarios creados:"
            print(label)
            for email in created:
                role_code = next(
                    r for r, local, _ in _ACCOUNTS if f"{local}@{email_domain}" == email
                )
                print(f"  - {email}  (rol: {role_code})")
        if skipped:
            print("Usuarios existentes (sin cambios):")
            for email in skipped:
                print(f"  - {email}")
        if not created and not skipped:
            print("Nada que hacer.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clinic-name",
        required=True,
        help='Nombre de la organizacion y de la sucursal, p. ej. "Clinica EMO".',
    )
    parser.add_argument(
        "--email-domain",
        required=True,
        help="Dominio de los 3 correos, p. ej. clinica.emo (sin arroba).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Muestra que haria sin escribir nada en la base de datos.",
    )
    args = parser.parse_args()

    password = os.environ.get("BOOTSTRAP_PASSWORD")
    if not password:
        print(
            "Falta la variable de entorno BOOTSTRAP_PASSWORD. No se acepta por linea de "
            "comandos ni hay un valor por defecto -- ver el encabezado de este archivo.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    asyncio.run(
        _run(
            clinic_name=args.clinic_name,
            email_domain=args.email_domain,
            password=password,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
