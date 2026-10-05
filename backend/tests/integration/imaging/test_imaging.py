import io

from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patients.schemas import PatientCreateRequest
from app.modules.patients.service import create_patient


async def _login(client: AsyncClient, email: str, password: str = "Contrasena123") -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def _headers(token: str, clinic_id) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "X-Clinic-Id": str(clinic_id)}


def _jpeg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (400, 300), (120, 60, 30)).save(buffer, format="JPEG")
    return buffer.getvalue()


async def _setup(client: AsyncClient, make_user, clinic, db_session: AsyncSession):
    await make_user(email="odonto@example.com", role_code="odontologo")
    token = await _login(client, "odonto@example.com")
    headers = _headers(token, clinic.id)

    patient = await create_patient(
        db_session,
        clinic_id=clinic.id,
        data=PatientCreateRequest(
            first_name="Jose", last_name_paternal="Perez", date_of_birth="1990-05-20"
        ),
        actor_id=None,
    )
    encounter_resp = await client.post(
        "/api/v1/encounters", headers=headers, json={"patient_id": str(patient.id)}
    )
    assert encounter_resp.status_code == 201, encounter_resp.text
    return headers, str(patient.id), encounter_resp.json()["id"]


async def test_upload_single_image_with_metadata(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/images",
        headers=headers,
        data={"encounter_id": encounter_id, "study_type": "periapical", "tooth_fdi": "36"},
        files={"files": ("rx36.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body) == 1
    assert body[0]["study_type"] == "periapical"
    assert body[0]["tooth_fdi"] == 36
    assert body[0]["has_thumbnail"] is True


async def test_upload_multiple_images_in_one_request(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/images",
        headers=headers,
        data={"encounter_id": encounter_id, "study_type": "intraoral"},
        files=[
            ("files", ("foto1.jpg", _jpeg_bytes(), "image/jpeg")),
            ("files", ("foto2.jpg", _jpeg_bytes(), "image/jpeg")),
        ],
    )
    assert response.status_code == 201, response.text
    assert len(response.json()) == 2

    listed = await client.get(f"/api/v1/patients/{patient_id}/images", headers=headers)
    assert len(listed.json()) == 2


async def test_upload_rejects_invalid_file_type(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/images",
        headers=headers,
        data={"encounter_id": encounter_id, "study_type": "intraoral"},
        files={"files": ("nota.txt", b"hola", "text/plain")},
    )
    assert response.status_code == 400


async def test_upload_rejects_invalid_tooth(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    response = await client.post(
        f"/api/v1/patients/{patient_id}/images",
        headers=headers,
        data={"encounter_id": encounter_id, "study_type": "periapical", "tooth_fdi": "19"},
        files={"files": ("rx.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_TOOTH"


async def test_get_image_and_thumbnail_bytes(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)

    created = await client.post(
        f"/api/v1/patients/{patient_id}/images",
        headers=headers,
        data={"encounter_id": encounter_id, "study_type": "intraoral"},
        files={"files": ("foto.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    image_id = created.json()[0]["id"]

    full = await client.get(f"/api/v1/images/{image_id}", headers=headers)
    assert full.status_code == 200
    assert full.headers["content-type"] == "image/jpeg"

    thumb = await client.get(f"/api/v1/images/{image_id}/thumbnail", headers=headers)
    assert thumb.status_code == 200
    assert thumb.headers["content-type"] == "image/jpeg"
    assert len(thumb.content) < len(full.content)


async def test_annul_image_requires_reason(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    created = await client.post(
        f"/api/v1/patients/{patient_id}/images",
        headers=headers,
        data={"encounter_id": encounter_id, "study_type": "intraoral"},
        files={"files": ("foto.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    image_id = created.json()[0]["id"]

    without_reason = await client.post(f"/api/v1/images/{image_id}/annul", headers=headers, json={})
    assert without_reason.status_code == 422

    with_reason = await client.post(
        f"/api/v1/images/{image_id}/annul",
        headers=headers,
        json={"reason": "Imagen subida al paciente equivocado"},
    )
    assert with_reason.status_code == 200
    assert with_reason.json()["is_active"] is False


async def test_upload_denied_for_role_without_imaging_write(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    await make_user(email="recepcion@example.com", role_code="recepcion")
    recepcion_token = await _login(client, "recepcion@example.com")

    response = await client.post(
        f"/api/v1/patients/{patient_id}/images",
        headers=_headers(recepcion_token, clinic.id),
        data={"encounter_id": encounter_id, "study_type": "intraoral"},
        files={"files": ("foto.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    assert response.status_code == 403


async def test_filter_images_by_study_type(
    client: AsyncClient, make_user, clinic, db_session: AsyncSession
) -> None:
    headers, patient_id, encounter_id = await _setup(client, make_user, clinic, db_session)
    await client.post(
        f"/api/v1/patients/{patient_id}/images",
        headers=headers,
        data={"encounter_id": encounter_id, "study_type": "intraoral"},
        files={"files": ("foto.jpg", _jpeg_bytes(), "image/jpeg")},
    )
    await client.post(
        f"/api/v1/patients/{patient_id}/images",
        headers=headers,
        data={"encounter_id": encounter_id, "study_type": "panoramica"},
        files={"files": ("pano.jpg", _jpeg_bytes(), "image/jpeg")},
    )

    filtered = await client.get(
        f"/api/v1/patients/{patient_id}/images?study_type=panoramica", headers=headers
    )
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["study_type"] == "panoramica"
