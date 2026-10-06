from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Fase 12: cabeceras de seguridad (OWASP Secure Headers). /docs, /redoc y /openapi.json
# quedan fuera del Content-Security-Policy porque Swagger UI/Redoc cargan su propio
# bundle de un CDN -- esas rutas ya se desactivan por completo en produccion (ver
# app.main, environment == "production").
_DOCS_PATHS = {"/docs", "/redoc", "/openapi.json"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: Starlette, environment: str) -> None:
        super().__init__(app)
        self._environment = environment

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), geolocation=(), microphone=(), payment=(), usb=()"
        )
        if request.url.path not in _DOCS_PATHS:
            response.headers["Content-Security-Policy"] = "default-src 'none'"
        if self._environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"

        return response
