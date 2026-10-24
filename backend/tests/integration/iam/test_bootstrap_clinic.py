from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap_clinic import bootstrap
from app.core.security import verify_password
from app.modules.iam.models import Role, User, UserClinic


async def test_creates_exactly_the_three_accounts_with_the_right_roles(
    db_session: AsyncSession,
) -> None:
    created, skipped = await bootstrap(
        db_session,
        clinic_name="Clinica EMO",
        email_domain="clinica.emo",
        # Contrasena de prueba arbitraria -- nunca la real que usa la clinica
        # de verdad, para no acoplar este archivo versionado a un secreto.
        password="PruebaArbitraria123",
    )

    assert set(created) == {
        "agenda@clinica.emo",
        "admin@clinica.emo",
        "odontologo@clinica.emo",
    }
    assert skipped == []

    users = (
        await db_session.execute(select(User).where(User.email.like("%@clinica.emo")))
    ).scalars().all()
    assert len(users) == 3
    for user in users:
        assert verify_password("PruebaArbitraria123", user.hashed_password)

    rows = await db_session.execute(
        select(User.email, Role.code)
        .join(UserClinic, UserClinic.user_id == User.id)
        .join(Role, Role.id == UserClinic.role_id)
        .where(User.email.like("%@clinica.emo"))
    )
    roles_by_email = dict(rows.all())
    assert roles_by_email == {
        "agenda@clinica.emo": "recepcion",
        "admin@clinica.emo": "admin_clinica",
        "odontologo@clinica.emo": "odontologo",
    }


async def test_running_it_twice_does_not_duplicate_users(db_session: AsyncSession) -> None:
    await bootstrap(
        db_session, clinic_name="Clinica EMO", email_domain="clinica.emo", password="x"
    )

    created, skipped = await bootstrap(
        db_session, clinic_name="Clinica EMO", email_domain="clinica.emo", password="x"
    )

    assert created == []
    assert set(skipped) == {"agenda@clinica.emo", "admin@clinica.emo", "odontologo@clinica.emo"}

    users = (
        await db_session.execute(select(User).where(User.email.like("%@clinica.emo")))
    ).scalars().all()
    assert len(users) == 3


async def test_dry_run_reports_without_writing_anything(db_session: AsyncSession) -> None:
    created, skipped = await bootstrap(
        db_session,
        clinic_name="Clinica EMO",
        email_domain="clinica.emo",
        password="x",
        dry_run=True,
    )

    assert set(created) == {"agenda@clinica.emo", "admin@clinica.emo", "odontologo@clinica.emo"}
    assert skipped == []

    users = (
        await db_session.execute(select(User).where(User.email.like("%@clinica.emo")))
    ).scalars().all()
    assert users == []
