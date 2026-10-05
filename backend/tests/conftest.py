from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.db import get_db
from app.core.security import hash_password
from app.main import app
from app.modules.iam.models import Clinic, Organization, Role, User, UserClinic

TEST_DATABASE_URL = "postgresql+asyncpg://dentia:dentia@localhost:5432/dentia_test"

# NullPool: pytest-asyncio usa un event loop nuevo por prueba (function scope) y en
# Windows reutilizar una conexion asyncpg de un loop ya cerrado rompe con un
# AttributeError de asyncio. Sin pool, cada conexion es nueva y se descarta al salir.
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)

TRANSACTIONAL_TABLES = (
    "audit_events",
    "user_clinics",
    "refresh_tokens",
    "clinics",
    "organizations",
    "users",
)


@pytest.fixture(scope="session", autouse=True)
def _apply_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parent.parent
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(cfg, "head")


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables() -> AsyncIterator[None]:
    async with test_engine.begin() as conn:
        await conn.execute(
            text(f"TRUNCATE TABLE {', '.join(TRANSACTIONAL_TABLES)} RESTART IDENTITY CASCADE")
        )
    yield


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    previous_sessionmaker = app.state.db_sessionmaker
    app.state.db_sessionmaker = TestSessionLocal

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    app.state.db_sessionmaker = previous_sessionmaker


@pytest_asyncio.fixture
async def clinic(db_session: AsyncSession) -> Clinic:
    organization = Organization(name="Clinica de prueba")
    db_session.add(organization)
    await db_session.flush()

    clinic_row = Clinic(organization_id=organization.id, name="Sucursal Centro")
    db_session.add(clinic_row)
    await db_session.commit()
    return clinic_row


@pytest_asyncio.fixture
def make_user(db_session: AsyncSession, clinic: Clinic):
    async def _make_user(
        *,
        email: str = "dentista@example.com",
        password: str = "Contrasena123",
        role_code: str = "odontologo",
        mfa_enabled: bool = False,
        mfa_secret: str | None = None,
    ) -> User:
        role = (await db_session.execute(select(Role).where(Role.code == role_code))).scalar_one()
        user = User(
            email=email,
            full_name="Usuario de prueba",
            hashed_password=hash_password(password),
            mfa_enabled=mfa_enabled,
            mfa_secret=mfa_secret,
        )
        db_session.add(user)
        await db_session.flush()

        db_session.add(UserClinic(user_id=user.id, clinic_id=clinic.id, role_id=role.id))
        await db_session.commit()
        return user

    return _make_user
