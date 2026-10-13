import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.odontogram import service as odontogram_service
from app.modules.patients.schemas import PatientCreateRequest
from app.modules.patients.service import create_patient


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _headers(token: str, clinic_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic_id)}


async def _odontologo_token(client: AsyncClient, make_user, clinic) -> str:
    await make_user(email="odonto@example.com", role_code="odontologo")
    return await _login(client, "odonto@example.com")


async def _make_patient(db_session: AsyncSession, clinic, actor_id) -> str:
    patient = await create_patient(
        db_session,
        clinic_id=clinic.id,
        data=PatientCreateRequest(
            first_name="Jose", last_name_paternal="Perez", date_of_birth="1990-05-20"
        ),
        actor_id=actor_id,
    )
    return str(patient.id)


async def _create_encounter(client: AsyncClient, headers: dict, patient_id: str) -> str:
    response = await client.post(
        "/api/v1/encounters", headers=headers, json={"patient_id": patient_id}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _setup(client: AsyncClient, make_user, clinic, db_session: AsyncSession):
    token = await _odontologo_token(client, make_user, clinic)
    headers = _headers(token, clinic.id)
    patient_id = await _make_patient(db_session, clinic, None)
    encounter_id = await _create_encounter(client, headers, patient_id)
    return headers, patient_id, encounter_id


async def test_create_finding_denied_without_odontogram_write(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    await make_user(email="recepcion@example.com", role_code="recepcion")
    recepcion_token = await _login(client, "recepcion@example.com")

    response = await client.post(
        "/api/v1/tooth-findings",
        headers=_headers(recepcion_token, clinic.id),
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "finding_code": "caries",
        },
    )
    assert response.status_code == 403


async def test_create_finding_rejects_invalid_tooth(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 19,
            "finding_code": "caries",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_TOOTH"


async def test_create_finding_rejects_invalid_surface_for_tooth(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    # pieza 16 es posterior: no tiene superficie incisal
    response = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 16,
            "surface": "I",
            "finding_code": "caries",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_SURFACE"


async def test_whole_tooth_finding_accepts_null_surface(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 18,
            "finding_code": "ausente",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["surface"] is None


async def test_create_finding_rejects_a_code_not_in_the_clinic_catalog(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """B1 (Parte B, Fase 12.2): 'Hallazgos del odontograma' ya no es un Literal fijo,
    sino el catalogo administrable de la sucursal."""
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "finding_code": "no_existe",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_FINDING_CODE"


async def test_create_finding_requires_surface_when_the_catalog_item_says_so(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """'caries' esta marcado requires_surface=True en el catalogo (antes la
    superficie siempre era opcional sin importar el hallazgo)."""
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "finding_code": "caries",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "SURFACE_REQUIRED"


async def test_odontogram_shows_only_current_findings(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "finding_code": "caries",
        },
    )

    odontogram = await client.get(f"/api/v1/patients/{patient_id}/odontogram", headers=headers)
    assert odontogram.status_code == 200
    findings = odontogram.json()
    assert len(findings) == 1
    assert findings[0]["finding_code"] == "caries"
    assert findings[0]["is_current"] is True


async def test_successive_findings_supersede_and_keep_history(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """Prueba obligatoria (regla 5 de CLAUDE.md): cambios sucesivos sobre la misma
    pieza/superficie conservan el historial completo, no lo sobrescriben."""
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    caries = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "finding_code": "caries",
        },
    )
    assert caries.status_code == 201
    caries_id = caries.json()["id"]

    restauracion = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "finding_code": "restauracion",
            "material": "resina",
        },
    )
    assert restauracion.status_code == 201
    restauracion_body = restauracion.json()
    assert restauracion_body["supersedes_id"] == caries_id
    assert restauracion_body["is_current"] is True

    odontogram = await client.get(f"/api/v1/patients/{patient_id}/odontogram", headers=headers)
    findings = odontogram.json()
    assert len(findings) == 1
    assert findings[0]["finding_code"] == "restauracion"

    history = await client.get(f"/api/v1/patients/{patient_id}/teeth/36/history", headers=headers)
    assert history.status_code == 200
    entries = history.json()
    assert [e["finding_code"] for e in entries] == ["restauracion", "caries"]
    assert entries[1]["is_current"] is False
    assert entries[0]["author_name"]


async def test_get_odontogram_at_past_date_reconstructs_state(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    caries = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "finding_code": "caries",
        },
    )
    caries_id = caries.json()["id"]
    await db_session.execute(
        text("UPDATE tooth_findings SET created_at = :ts WHERE id = :id"),
        {"ts": datetime(2020, 1, 1, tzinfo=UTC), "id": caries_id},
    )
    await db_session.commit()

    # "hoy": se corrige por una restauracion (created_at = ahora, por defecto)
    restauracion = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "finding_code": "restauracion",
        },
    )
    assert restauracion.status_code == 201

    past = await client.get(
        f"/api/v1/patients/{patient_id}/odontogram",
        headers=headers,
        params={"at": "2020-06-01"},
    )
    assert past.status_code == 200
    past_findings = past.json()
    assert len(past_findings) == 1
    assert past_findings[0]["finding_code"] == "caries"

    current = await client.get(f"/api/v1/patients/{patient_id}/odontogram", headers=headers)
    assert current.json()[0]["finding_code"] == "restauracion"


async def test_retire_finding_marks_it_not_current(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    """ "deshaz" de Dentia (13.3, sec. 6.5 del diseno): nunca borra (regla 2 de
    CLAUDE.md) -- el hallazgo se queda en la tabla, solo deja de contar como
    vigente."""
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    odonto = (
        await db_session.execute(text("SELECT id FROM users WHERE email = 'odonto@example.com'"))
    ).scalar_one()

    caries = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "finding_code": "caries",
        },
    )
    assert caries.status_code == 201
    caries_id = caries.json()["id"]

    await odontogram_service.retire_finding(
        db_session,
        clinic_id=clinic.id,
        patient_id=uuid.UUID(patient_id),
        finding_id=uuid.UUID(caries_id),
        actor_id=odonto,
    )

    odontogram = await client.get(f"/api/v1/patients/{patient_id}/odontogram", headers=headers)
    assert odontogram.json() == []

    history = await client.get(f"/api/v1/patients/{patient_id}/teeth/36/history", headers=headers)
    entries = history.json()
    assert len(entries) == 1
    assert entries[0]["is_current"] is False


async def test_retire_finding_reactivates_the_one_it_superseded(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    odonto = (
        await db_session.execute(text("SELECT id FROM users WHERE email = 'odonto@example.com'"))
    ).scalar_one()

    caries = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "finding_code": "caries",
        },
    )
    caries_id = caries.json()["id"]

    restauracion = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "finding_code": "restauracion",
        },
    )
    restauracion_id = restauracion.json()["id"]

    await odontogram_service.retire_finding(
        db_session,
        clinic_id=clinic.id,
        patient_id=uuid.UUID(patient_id),
        finding_id=uuid.UUID(restauracion_id),
        actor_id=odonto,
    )

    odontogram = await client.get(f"/api/v1/patients/{patient_id}/odontogram", headers=headers)
    findings = odontogram.json()
    assert len(findings) == 1
    assert findings[0]["id"] == caries_id
    assert findings[0]["finding_code"] == "caries"


async def test_retire_finding_already_retired_raises(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    odonto = (
        await db_session.execute(text("SELECT id FROM users WHERE email = 'odonto@example.com'"))
    ).scalar_one()

    caries = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "finding_code": "caries",
        },
    )
    caries_id = caries.json()["id"]

    await odontogram_service.retire_finding(
        db_session,
        clinic_id=clinic.id,
        patient_id=uuid.UUID(patient_id),
        finding_id=uuid.UUID(caries_id),
        actor_id=odonto,
    )

    with pytest.raises(AppError) as exc_info:
        await odontogram_service.retire_finding(
            db_session,
            clinic_id=clinic.id,
            patient_id=uuid.UUID(patient_id),
            finding_id=uuid.UUID(caries_id),
            actor_id=odonto,
        )
    assert exc_info.value.code == "FINDING_NOT_CURRENT"


# ----------------------------------------------- B12 (M5): POST /tooth-findings/{id}/annul


async def test_annul_finding_marks_it_not_current_and_requires_a_reason(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    caries = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "finding_code": "caries",
        },
    )
    caries_id = caries.json()["id"]

    missing_reason = await client.post(
        f"/api/v1/tooth-findings/{caries_id}/annul", headers=headers, json={"reason": ""}
    )
    assert missing_reason.status_code == 422

    annulled = await client.post(
        f"/api/v1/tooth-findings/{caries_id}/annul",
        headers=headers,
        json={"reason": "Se capturó en la pieza equivocada"},
    )
    assert annulled.status_code == 200
    assert annulled.json()["is_current"] is False

    odontogram = await client.get(f"/api/v1/patients/{patient_id}/odontogram", headers=headers)
    assert odontogram.json() == []

    history = await client.get(f"/api/v1/patients/{patient_id}/teeth/36/history", headers=headers)
    assert history.json()[0]["is_current"] is False


async def test_annul_finding_reactivates_the_one_it_superseded(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    caries = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "finding_code": "caries",
        },
    )
    caries_id = caries.json()["id"]

    restauracion = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "finding_code": "restauracion",
        },
    )
    restauracion_id = restauracion.json()["id"]

    annulled = await client.post(
        f"/api/v1/tooth-findings/{restauracion_id}/annul",
        headers=headers,
        json={"reason": "No se realizó la restauración, fue un registro por error"},
    )
    assert annulled.status_code == 200

    odontogram = await client.get(f"/api/v1/patients/{patient_id}/odontogram", headers=headers)
    findings = odontogram.json()
    assert len(findings) == 1
    assert findings[0]["id"] == caries_id
    assert findings[0]["finding_code"] == "caries"


async def test_annul_finding_already_annulled_is_a_conflict(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    caries = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "finding_code": "caries",
        },
    )
    caries_id = caries.json()["id"]

    first = await client.post(
        f"/api/v1/tooth-findings/{caries_id}/annul", headers=headers, json={"reason": "Motivo 1"}
    )
    assert first.status_code == 200

    second = await client.post(
        f"/api/v1/tooth-findings/{caries_id}/annul", headers=headers, json={"reason": "Motivo 2"}
    )
    assert second.status_code == 409
    assert second.json()["code"] == "FINDING_NOT_CURRENT"


async def test_annul_finding_denied_without_odontogram_write(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    caries = await client.post(
        "/api/v1/tooth-findings",
        headers=headers,
        json={
            "patient_id": patient_id,
            "encounter_id": encounter_id,
            "tooth_fdi": 36,
            "surface": "O",
            "finding_code": "caries",
        },
    )
    caries_id = caries.json()["id"]

    await make_user(email="recepcion@example.com", role_code="recepcion")
    recepcion_token = await _login(client, "recepcion@example.com")

    response = await client.post(
        f"/api/v1/tooth-findings/{caries_id}/annul",
        headers=_headers(recepcion_token, clinic.id),
        json={"reason": "Intento sin permiso"},
    )
    assert response.status_code == 403


async def test_annul_finding_not_found_is_404(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, _patient_id, _encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/tooth-findings/{uuid.uuid4()}/annul",
        headers=headers,
        json={"reason": "No existe"},
    )
    assert response.status_code == 404
