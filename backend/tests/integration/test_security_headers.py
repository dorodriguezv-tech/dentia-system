from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_health_response_includes_security_headers() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "microphone=()" in response.headers["Permissions-Policy"]
    assert response.headers["Content-Security-Policy"] == "default-src 'none'"
    # environment por defecto en pruebas es "development": sin HSTS (HTTP, no HTTPS).
    assert "Strict-Transport-Security" not in response.headers


async def test_docs_routes_not_csp_restricted_in_development() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs")

    assert response.status_code == 200
    assert "Content-Security-Policy" not in response.headers
