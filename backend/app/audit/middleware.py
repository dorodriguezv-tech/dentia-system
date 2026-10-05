from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.audit import service as audit_service
from app.core.db import async_session_factory


class AccessDeniedAuditMiddleware(BaseHTTPMiddleware):
    """Registra en AuditEvent cada respuesta 403 (acceso denegado).

    Usa ``request.app.state.db_sessionmaker`` en vez del sessionmaker global
    para que las pruebas puedan sustituirlo por el de la base de datos de
    pruebas (esta clase no pasa por el sistema de dependencias de FastAPI).
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        if response.status_code == 403:
            user = getattr(request.state, "user", None)
            clinic_id = getattr(request.state, "clinic_id", None)
            sessionmaker = getattr(request.app.state, "db_sessionmaker", async_session_factory)
            async with sessionmaker() as session:
                await audit_service.log(
                    session,
                    action="access_denied",
                    actor_user_id=user.id if user else None,
                    clinic_id=clinic_id,
                    entity_type="http_request",
                    entity_id=request.url.path,
                    details={"method": request.method},
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
                await session.commit()

        return response
