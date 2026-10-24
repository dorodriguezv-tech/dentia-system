from httpx import AsyncClient

from app.core.db import get_db
from app.main import app


async def test_health_ok(client: AsyncClient) -> None:
    # Usa la fixture `client` (NullPool, ver tests/conftest.py) a proposito, no
    # un AsyncClient aparte contra `app` directo: el motor real de la app
    # (`app/core/db.py::engine`) reutiliza conexiones entre pruebas y, al
    # entremezclarse con el event loop nuevo que pytest-asyncio crea por
    # prueba, una conexion pooled de un loop ya cerrado produce un 503
    # intermitente -- no es un fallo real de /health, solo un artefacto de
    # golpear el motor sin pool de pruebas dos veces seguidas en crudo.
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_fails_when_the_database_is_unreachable(client: AsyncClient) -> None:
    """Fase "Publicacion en Hostinger" sec. 6, cambio #8: sin tocar la base,
    una API "viva" pero desconectada de PostgreSQL se reportaria como sana
    tanto al healthcheck de Docker como al monitor externo cuando no lo esta."""

    class _BrokenSession:
        async def execute(self, *_args: object, **_kwargs: object) -> None:
            raise ConnectionRefusedError("simulated: PostgreSQL unreachable")

    async def _override_get_db():
        yield _BrokenSession()

    app.dependency_overrides[get_db] = _override_get_db
    try:
        response = await client.get("/api/v1/health")
    finally:
        del app.dependency_overrides[get_db]

    assert response.status_code == 503
    assert response.json()["code"] == "DATABASE_UNAVAILABLE"
