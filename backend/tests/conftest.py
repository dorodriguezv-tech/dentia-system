import shutil
import tempfile
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
from app.core.storage import LocalStorageBackend, get_storage_backend
from app.main import app
from app.modules.catalogs.models import ClinicCatalogItem
from app.modules.iam.models import Clinic, Organization, Role, User, UserClinic
from app.seed import CATALOG_SEEDS

TEST_DATABASE_URL = "postgresql+asyncpg://dentia:dentia@localhost:5432/dentia_test"

# NullPool: pytest-asyncio usa un event loop nuevo por prueba (function scope) y en
# Windows reutilizar una conexion asyncpg de un loop ya cerrado rompe con un
# AttributeError de asyncio. Sin pool, cada conexion es nueva y se descarta al salir.
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)

TRANSACTIONAL_TABLES = (
    "voice_command_logs",
    "audit_events",
    "ai_suggestions",
    "ai_clinic_settings",
    "images",
    "consents",
    "document_templates",
    "clinic_branding",
    "clinic_document_settings",
    "clinic_catalog_items",
    "medical_history",
    "allergies",
    "medications",
    "vital_signs",
    "family_history_entries",
    "personal_pathological_histories",
    "personal_non_pathological_histories",
    "systems_review_entries",
    "odontological_exams",
    "periodontal_anamneses",
    "radiographic_analyses",
    "odontogram_diagnosis_details",
    "parallelometer_analyses",
    "removable_partial_denture_designs",
    "tooth_diagnosis_entries",
    "tooth_treatment_plan_entries",
    "endodontic_interrogations",
    "endodontic_pulp_sensitivity_tests",
    "endodontic_periodontal_tests",
    "endodontic_radiographic_interpretations",
    "endodontic_diagnosis_treatments",
    "endodontic_tooth_diagnosis_codes",
    "endodontic_working_lengths",
    "clinical_notes",
    "tooth_findings",
    "payment_allocations",
    "payments",
    "cash_sessions",
    "clinic_billing_settings",
    "charges",
    "procedures_performed",
    "procedures_planned",
    "treatment_phases",
    "treatment_plans",
    "procedure_catalog",
    "diagnoses",
    "reminder_tasks",
    "appointment_status_history",
    "waitlist_entries",
    "provider_blocks",
    "provider_working_hours",
    "encounters",
    "appointments",
    "resources",
    "providers",
    "patient_contacts",
    "patients",
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


@pytest_asyncio.fixture(autouse=True)
async def _reset_voice_tts_worker() -> AsyncIterator[None]:
    """Dentia (Fase 13): app/voice/tts.py mantiene un subproceso de Piper vivo
    entre llamadas (para no pagar ~3 s de arranque por frase). Ese subproceso
    queda atado al event loop de asyncio que lo creo -- pytest-asyncio crea un
    loop nuevo por prueba (asyncio_default_fixture_loop_scope = "function"), y
    reusar el mismo proceso desde el loop de la SIGUIENTE prueba corrompe sus
    pipes. Se apaga despues de cada prueba para que la siguiente arranque uno
    propio si lo necesita."""
    yield
    from app.voice import tts as voice_tts

    await voice_tts.shutdown()


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def _override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    storage_dir = Path(tempfile.mkdtemp(prefix="dentia-test-storage-"))
    test_storage = LocalStorageBackend(storage_dir)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_storage_backend] = lambda: test_storage
    previous_sessionmaker = app.state.db_sessionmaker
    app.state.db_sessionmaker = TestSessionLocal

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    app.state.db_sessionmaker = previous_sessionmaker
    shutil.rmtree(storage_dir, ignore_errors=True)


@pytest_asyncio.fixture
async def clinic(db_session: AsyncSession) -> Clinic:
    organization = Organization(name="Clinica de prueba")
    db_session.add(organization)
    await db_session.flush()

    clinic_row = Clinic(organization_id=organization.id, name="Sucursal Centro")
    db_session.add(clinic_row)
    await db_session.flush()

    # B1 (Parte B): agenda/odontogram/diagnosis/records ya no validan contra
    # constantes fijas, sino contra este catalogo -- toda prueba que agende una
    # cita, registre un hallazgo o un diagnostico necesita uno real. Insertado
    # directo por ORM (no via catalogs_service, que hace un commit por item) para
    # no sumarle ~39 commits a cada prueba que use este fixture.
    db_session.add_all(
        ClinicCatalogItem(
            clinic_id=clinic_row.id,
            catalog_type=catalog_type,
            code=code,
            name=name,
            sort_order=sort_order,
            extra=extra,
        )
        for catalog_type, code, name, sort_order, extra in CATALOG_SEEDS
    )
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
