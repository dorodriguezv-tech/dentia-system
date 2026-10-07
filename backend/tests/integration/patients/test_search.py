import pytest
from httpx import AsyncClient

from tests.integration.patients.test_patients import _create_recepcion_token, _headers

TARGET_PATIENT = {
    "first_name": "Juan Carlos",
    "last_name_paternal": "Perez",
    "last_name_maternal": "Lopez",
    "date_of_birth": "1980-01-15",
    "phone": "555-123-4567",
    "email": "juan.perez@example.com",
}

# Paciente "ruido": nombre distinto, para confirmar que la busqueda no trae a todo el
# mundo (un umbral demasiado bajo seria tan inutil como uno demasiado alto).
OTHER_PATIENT = {
    "first_name": "Maria",
    "last_name_paternal": "Gonzalez",
    "last_name_maternal": "Ruiz",
    "date_of_birth": "1975-03-10",
    "phone": "555-999-0000",
    "email": "maria.gonzalez@example.com",
}


async def _seed(client: AsyncClient, make_user, clinic) -> tuple[str, str]:
    """Crea los dos pacientes y regresa (token_recepcion, expediente_de_juan)."""
    token = await _create_recepcion_token(client, make_user, clinic)
    headers = _headers(token, clinic.id)
    juan = await client.post("/api/v1/patients", headers=headers, json=TARGET_PATIENT)
    await client.post("/api/v1/patients", headers=headers, json=OTHER_PATIENT)
    return token, juan.json()["expediente_number"]


@pytest.mark.parametrize(
    "q",
    [
        "perez",
        "Pérez",
        "PEREZ LOPEZ",
        "lopez perez",
        "jua per",
        "Peres",  # error de una letra (A2, caso de aceptacion)
    ],
)
async def test_search_finds_juan_perez_lopez(
    client: AsyncClient, make_user, clinic, q: str
) -> None:
    """A2: la busqueda debe encontrar coincidencias parciales dentro del nombre
    completo (no solo si el texto completo es parecido al nombre completo), apellidos
    en cualquier orden, y tolerar un error de una letra."""
    token, _ = await _seed(client, make_user, clinic)

    response = await client.get(
        "/api/v1/patients/search", params={"q": q}, headers=_headers(token, clinic.id)
    )

    assert response.status_code == 200
    names = [p["full_name"] for p in response.json()]
    msg = f'"{q}" no encontro a Juan Carlos Perez Lopez (resultados: {names})'
    assert any("Perez Lopez" in n for n in names), msg
    assert "Maria Gonzalez Ruiz" not in names, f'"{q}" trajo tambien a un paciente sin relacion'


async def test_search_by_expediente_number_exact(client: AsyncClient, make_user, clinic) -> None:
    token, expediente = await _seed(client, make_user, clinic)

    response = await client.get(
        "/api/v1/patients/search", params={"q": expediente}, headers=_headers(token, clinic.id)
    )

    assert response.status_code == 200
    assert any(p["expediente_number"] == expediente for p in response.json())


@pytest.mark.parametrize("q", ["5551234567", "555-123-4567", "(555) 123-4567"])
async def test_search_by_phone_ignores_formatting(
    client: AsyncClient, make_user, clinic, q: str
) -> None:
    token, _ = await _seed(client, make_user, clinic)

    response = await client.get(
        "/api/v1/patients/search", params={"q": q}, headers=_headers(token, clinic.id)
    )

    assert response.status_code == 200
    names = [p["full_name"] for p in response.json()]
    msg = f'"{q}" no encontro por telefono (resultados: {names})'
    assert any("Perez Lopez" in n for n in names), msg
