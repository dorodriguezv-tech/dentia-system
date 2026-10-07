import uuid
from collections.abc import Awaitable, Callable

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import TokenError, decode_token
from app.modules.iam.models import Permission, Role, RolePermission, User, UserClinic


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError("UNAUTHENTICATED", "Falta el token de acceso", status_code=401)

    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_token(token, expected_type="access")
    except TokenError as exc:
        raise AppError("UNAUTHENTICATED", str(exc), status_code=401) from exc

    user_id = uuid.UUID(payload["sub"])
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError("UNAUTHENTICATED", "Usuario invalido o inactivo", status_code=401)

    request.state.user = user
    return user


async def get_clinic_id(
    request: Request,
    x_clinic_id: str = Header(..., alias="X-Clinic-Id"),
) -> uuid.UUID:
    try:
        clinic_id = uuid.UUID(x_clinic_id)
    except ValueError as exc:
        raise AppError("INVALID_CLINIC", "X-Clinic-Id invalido", status_code=400) from exc

    request.state.clinic_id = clinic_id
    return clinic_id


async def user_has_any_permission(
    db: AsyncSession, *, user_id: uuid.UUID, clinic_id: uuid.UUID, codes: tuple[str, ...]
) -> bool:
    stmt = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserClinic, UserClinic.role_id == Role.id)
        .where(
            UserClinic.user_id == user_id,
            UserClinic.clinic_id == clinic_id,
            Permission.code.in_(codes),
        )
    )
    result = await db.execute(stmt)
    return result.first() is not None


def require_permission(code: str) -> Callable[..., Awaitable[User]]:
    async def dependency(
        current_user: User = Depends(get_current_user),
        clinic_id: uuid.UUID = Depends(get_clinic_id),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        allowed = await user_has_any_permission(
            db, user_id=current_user.id, clinic_id=clinic_id, codes=(code,)
        )
        if not allowed:
            raise AppError("FORBIDDEN", "No tienes permiso para esta accion", status_code=403)
        return current_user

    return dependency


def require_any_permission(*codes: str) -> Callable[..., Awaitable[User]]:
    """Como `require_permission`, pero pasa si el usuario tiene **alguno** de los
    permisos dados. Util para un endpoint que varios roles con permisos distintos
    necesitan leer (p.ej. GET /catalogs/{tipo}, Fase 12.2 Parte B1: cada tipo de
    catalogo lo usa un modulo clinico distinto, mas `catalogs.manage` para quien
    los administra sin tener el permiso clinico de ese modulo)."""

    async def dependency(
        current_user: User = Depends(get_current_user),
        clinic_id: uuid.UUID = Depends(get_clinic_id),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        allowed = await user_has_any_permission(
            db, user_id=current_user.id, clinic_id=clinic_id, codes=codes
        )
        if not allowed:
            raise AppError("FORBIDDEN", "No tienes permiso para esta accion", status_code=403)
        return current_user

    return dependency
