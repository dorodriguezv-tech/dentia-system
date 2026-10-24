"""Alta del primer administrador (Fase "Publicacion en Hostinger" sec. 6,
cambio #7). Separado de app.seed a proposito: el seed crea usuarios con una
contrasena de ejemplo conocida (DEMO_PASSWORD) y 50 pacientes ficticios --
nunca debe correr en produccion. Este comando no crea nada ficticio.

Es la pieza generica que usa scripts/create-admin.sh del paquete de Docker
(deploy/vps/): crea (o reutiliza, si ya existe) la Organization/Clinic por
nombre y da de alta exactamente UN usuario con rol admin_clinica.

Para una clinica con varias cuentas de arranque ya definidas de antemano
(como la instalacion propia en servidor de la clinica, no la de Hostinger),
usa en cambio app.bootstrap_clinic.

Uso interactivo (pide la contrasena sin mostrarla en pantalla, recomendado):

    python -m app.create_admin --clinic-name "Clinica EMO" --email
    admin@dentia.digital

Uso no interactivo (CI, scripts/create-admin.sh): la contrasena SOLO se lee
de la variable de entorno ADMIN_PASSWORD (nunca como argumento de linea de
comandos ni con un valor por defecto en el codigo), igual que
BOOTSTRAP_PASSWORD en app.bootstrap_clinic:

    $env:ADMIN_PASSWORD = "<contrasena>"
    python -m app.create_admin --clinic-name "Clinica EMO" --email
    admin@dentia.digital --non-interactive
"""

import argparse
import asyncio
import getpass
import os
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clinic_bootstrap import get_or_create_clinic, get_or_create_organization
from app.core.db import async_session_factory
from app.core.password_policy import password_policy_violations
from app.core.security import hash_password
from app.modules.iam.models import Role, User, UserClinic


async def _create_admin(
    db: AsyncSession, *, clinic_name: str, email: str, password: str
) -> bool:
    """Devuelve True si se creo la cuenta, False si ya existia (idempotente)."""
    organization = await get_or_create_organization(db, name=clinic_name)
    clinic = await get_or_create_clinic(db, organization=organization, name=clinic_name)
    role = (
        await db.execute(select(Role).where(Role.code == "admin_clinica"))
    ).scalar_one()

    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing is not None:
        await db.rollback()
        return False

    user = User(email=email, full_name="Administrador", hashed_password=hash_password(password))
    db.add(user)
    await db.flush()
    db.add(UserClinic(user_id=user.id, clinic_id=clinic.id, role_id=role.id))
    await db.commit()
    return True


def _read_password(*, non_interactive: bool) -> str:
    if non_interactive:
        password = os.environ.get("ADMIN_PASSWORD")
        if not password:
            print(
                "Falta la variable de entorno ADMIN_PASSWORD (--non-interactive no acepta "
                "la contrasena por linea de comandos).",
                file=sys.stderr,
            )
            raise SystemExit(1)
        return password

    while True:
        password = getpass.getpass("Contrasena del administrador: ")
        confirm = getpass.getpass("Confirma la contrasena: ")
        if password != confirm:
            print("Las contrasenas no coinciden, intenta de nuevo.", file=sys.stderr)
            continue
        violations = password_policy_violations(password)
        if violations:
            for v in violations:
                print(f"  - {v}", file=sys.stderr)
            continue
        return password


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clinic-name",
        required=True,
        help='Nombre de la organizacion y de la sucursal, p. ej. "Clinica EMO".',
    )
    parser.add_argument("--email", required=True, help="Correo del administrador.")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Lee la contrasena de ADMIN_PASSWORD en vez de pedirla en pantalla.",
    )
    args = parser.parse_args()

    password = _read_password(non_interactive=args.non_interactive)
    if args.non_interactive:
        violations = password_policy_violations(password)
        if violations:
            for v in violations:
                print(f"  - {v}", file=sys.stderr)
            raise SystemExit(1)

    async def _run() -> None:
        async with async_session_factory() as db:
            created = await _create_admin(
                db, clinic_name=args.clinic_name, email=args.email, password=password
            )
            if created:
                print(f"Administrador creado: {args.email} (clinica: {args.clinic_name})")
            else:
                print(f"{args.email} ya existia -- no se toco.")

    asyncio.run(_run())


if __name__ == "__main__":
    main()
