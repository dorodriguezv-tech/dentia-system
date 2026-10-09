"""Pendiente #47 (resto de C3, docs/PENDIENTES_CLINICOS.md): vocabulario de
Whisper por CONTEXTO -- catalogos administrables de la sucursal (B1) y
nombres de pacientes, que el vocabulario fijo (`app/ai/vocab/terms.py`) no
puede traer porque los define cada clinica."""

from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalogs import service as catalogs_service
from app.modules.catalogs.schemas import CatalogItemCreateRequest
from app.seed import CATALOG_SEEDS
from app.voice import vocab_context
from app.voice.context import ScreenContext
from tests.integration.voice.test_dialogue import (
    _create_appointment,
    _make_patient,
    _make_provider,
)


async def test_contextual_terms_includes_clinic_catalog_items_and_patients(
    client, make_user, clinic, db_session: AsyncSession
) -> None:
    admin = await make_user(email="admin.vocab@example.com", role_code="admin_clinica")
    await catalogs_service.create_item(
        db_session,
        clinic_id=clinic.id,
        catalog_type="appointment_type",
        data=CatalogItemCreateRequest(code="carillas_zafiro", name="Carillas de Zafiro"),
        actor_id=admin.id,
    )

    today_patient_id = await _make_patient(db_session, clinic, ("Xochitl", "Amescua"))
    provider_id = await _make_provider(
        client,
        make_user,
        clinic,
        db_session,
        full_name="Laura Ruiz",
        email="ruiz.vocab@example.com",
    )
    token_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin.vocab@example.com", "password": "Contrasena123"},
    )
    headers = {
        "Authorization": f"Bearer {token_resp.json()['access_token']}",
        "X-Clinic-Id": str(clinic.id),
    }
    today = date.today()
    await _create_appointment(
        client,
        headers,
        patient_id=today_patient_id,
        provider_id=provider_id,
        appointment_type="consulta",
        starts_at=datetime(today.year, today.month, today.day, 10, 0, tzinfo=UTC),
    )

    screen_patient_id = await _make_patient(db_session, clinic, ("Benigno", "Quintanilla"))

    terms = await vocab_context.contextual_terms(
        db_session,
        clinic_id=clinic.id,
        context=ScreenContext(patient_id=screen_patient_id),
    )

    assert "carillas de zafiro" in terms
    assert "xochitl amescua" in terms
    assert "benigno quintanilla" in terms


async def test_contextual_terms_is_just_the_seeded_catalogs_without_appointments_or_screen_patient(
    db_session: AsyncSession, clinic
) -> None:
    """La sucursal del fixture sí trae catalogos sembrados (ver conftest.py) --
    esto prueba el otro extremo: sin cita hoy ni paciente en pantalla, el
    resultado es exactamente esas etiquetas, nada de mas."""
    terms = await vocab_context.contextual_terms(
        db_session, clinic_id=clinic.id, context=ScreenContext()
    )
    expected = {name.lower() for _, _, name, _, _ in CATALOG_SEEDS}
    assert set(terms) == expected
