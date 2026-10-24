from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.create_admin import _create_admin
from app.modules.iam.models import Role, User, UserClinic


async def test_creates_the_admin_with_the_admin_clinica_role(db_session: AsyncSession) -> None:
    created = await _create_admin(
        db_session,
        clinic_name="Clinica Demo",
        email="admin@dentia.digital",
        password="UnaClaveSegura12",
    )

    assert created is True
    rows = await db_session.execute(
        select(User.email, Role.code)
        .join(UserClinic, UserClinic.user_id == User.id)
        .join(Role, Role.id == UserClinic.role_id)
        .where(User.email == "admin@dentia.digital")
    )
    row = rows.one()
    assert row == ("admin@dentia.digital", "admin_clinica")

    user = (
        await db_session.execute(select(User).where(User.email == "admin@dentia.digital"))
    ).scalar_one()
    assert verify_password("UnaClaveSegura12", user.hashed_password)


async def test_running_it_twice_does_not_duplicate_the_admin(db_session: AsyncSession) -> None:
    await _create_admin(
        db_session, clinic_name="Clinica Demo", email="admin@dentia.digital", password="x" * 12
    )

    created_again = await _create_admin(
        db_session, clinic_name="Clinica Demo", email="admin@dentia.digital", password="y" * 12
    )

    assert created_again is False
    users = (
        await db_session.execute(select(User).where(User.email == "admin@dentia.digital"))
    ).scalars().all()
    assert len(users) == 1
