import uuid
from datetime import UTC, datetime, timedelta

import pyotp
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.audit.models import AuditEvent
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    TokenError,
    create_access_token,
    create_mfa_token,
    decode_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.modules.iam import rules
from app.modules.iam.models import Clinic, RefreshToken, Role, User, UserClinic
from app.modules.iam.schemas import UserCreateRequest, UserUpdateRequest

settings = get_settings()


async def _recent_login_failures(db: AsyncSession, email: str) -> int:
    since = datetime.now(UTC) - timedelta(minutes=rules.LOGIN_LOCKOUT_WINDOW_MINUTES)
    stmt = select(func.count()).where(
        AuditEvent.action == "auth.login_failed",
        AuditEvent.occurred_at >= since,
        AuditEvent.details["email"].astext == email,
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def _issue_token_pair(
    db: AsyncSession, user: User, replaced_token: RefreshToken | None = None
) -> tuple[str, str, int]:
    access_token, _jti, _expires_at = create_access_token(user.id)

    refresh_value = generate_opaque_token()
    now = datetime.now(UTC)
    refresh_row = RefreshToken(
        user_id=user.id,
        token_hash=hash_opaque_token(refresh_value),
        issued_at=now,
        expires_at=now + timedelta(hours=settings.refresh_token_expire_hours),
    )
    db.add(refresh_row)
    await db.flush()

    if replaced_token is not None:
        replaced_token.revoked_at = now
        replaced_token.replaced_by_id = refresh_row.id

    return access_token, refresh_value, settings.access_token_expire_minutes * 60


async def login(
    db: AsyncSession, *, email: str, password: str, ip_address: str | None
) -> tuple[User | None, str | None, tuple[str, str, int] | None]:
    """Devuelve (user, mfa_token, tokens). Si mfa_token no es None, falta el paso MFA."""

    if await _recent_login_failures(db, email) >= rules.MAX_LOGIN_FAILURES:
        raise AppError(
            "RATE_LIMITED",
            "Demasiados intentos fallidos. Intenta de nuevo mas tarde.",
            status_code=429,
        )

    stmt = select(User).where(User.email == email)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        await audit_service.log(
            db,
            action="auth.login_failed",
            details={"email": email},
            ip_address=ip_address,
        )
        await db.commit()
        raise AppError("INVALID_CREDENTIALS", "Correo o contrasena incorrectos", status_code=401)

    if user.mfa_enabled:
        await db.commit()
        return user, create_mfa_token(user.id), None

    tokens = await _issue_token_pair(db, user)
    await audit_service.log(db, action="auth.login", actor_user_id=user.id, ip_address=ip_address)
    await db.commit()
    return user, None, tokens


async def login_with_mfa(
    db: AsyncSession, *, mfa_token: str, code: str, ip_address: str | None
) -> tuple[User, tuple[str, str, int]]:
    try:
        payload = decode_token(mfa_token, expected_type="mfa")
    except TokenError as exc:
        raise AppError(
            "INVALID_MFA_TOKEN", "Token de MFA invalido o expirado", status_code=401
        ) from exc

    user = await db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.mfa_enabled or not user.mfa_secret:
        raise AppError("INVALID_MFA_TOKEN", "Token de MFA invalido", status_code=401)

    if not pyotp.TOTP(user.mfa_secret).verify(code, valid_window=1):
        await audit_service.log(
            db, action="auth.mfa_failed", actor_user_id=user.id, ip_address=ip_address
        )
        await db.commit()
        raise AppError("INVALID_MFA_CODE", "Codigo de autenticacion incorrecto", status_code=401)

    tokens = await _issue_token_pair(db, user)
    await audit_service.log(db, action="auth.login", actor_user_id=user.id, ip_address=ip_address)
    await db.commit()
    return user, tokens


async def refresh_tokens(
    db: AsyncSession, *, refresh_token: str
) -> tuple[User, tuple[str, str, int]]:
    token_hash = hash_opaque_token(refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    row = (await db.execute(stmt)).scalar_one_or_none()

    now = datetime.now(UTC)
    if row is None or row.revoked_at is not None or row.expires_at < now:
        raise AppError(
            "INVALID_REFRESH_TOKEN", "Refresh token invalido o expirado", status_code=401
        )

    user = await db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise AppError("INVALID_REFRESH_TOKEN", "Usuario invalido o inactivo", status_code=401)

    tokens = await _issue_token_pair(db, user, replaced_token=row)
    await audit_service.log(db, action="auth.refresh", actor_user_id=user.id)
    await db.commit()
    return user, tokens


async def logout(db: AsyncSession, *, refresh_token: str) -> None:
    token_hash = hash_opaque_token(refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is not None and row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        await audit_service.log(db, action="auth.logout", actor_user_id=row.user_id)
        await db.commit()


async def _user_role_codes(db: AsyncSession, *, user_id: uuid.UUID) -> set[str]:
    stmt = (
        select(Role.code)
        .join(UserClinic, UserClinic.role_id == Role.id)
        .where(UserClinic.user_id == user_id)
    )
    return {row[0] for row in (await db.execute(stmt)).all()}


async def mfa_setup_required(db: AsyncSession, *, user: User) -> bool:
    """CLAUDE.md sec. 5: MFA obligatoria para admin_clinica (cualquier clinica)."""

    if user.mfa_enabled:
        return False

    role_codes = await _user_role_codes(db, user_id=user.id)
    return any(rules.role_requires_mfa(code) for code in role_codes)


async def get_my_clinics(db: AsyncSession, *, user_id: uuid.UUID) -> list[tuple[Clinic, Role]]:
    stmt = (
        select(Clinic, Role)
        .join(UserClinic, UserClinic.clinic_id == Clinic.id)
        .join(Role, Role.id == UserClinic.role_id)
        .where(UserClinic.user_id == user_id)
        .order_by(Clinic.name)
    )
    return [(clinic, role) for clinic, role in (await db.execute(stmt)).all()]


async def setup_mfa(db: AsyncSession, *, user: User) -> tuple[str, str]:
    secret = pyotp.random_base32()
    user.mfa_secret = secret
    await db.commit()
    otpauth_url = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="DentalCare")
    return secret, otpauth_url


async def enable_mfa(db: AsyncSession, *, user: User, code: str) -> None:
    if not user.mfa_secret:
        raise AppError("MFA_NOT_SETUP", "Primero genera un secreto de MFA", status_code=400)
    if not pyotp.TOTP(user.mfa_secret).verify(code, valid_window=1):
        raise AppError("INVALID_MFA_CODE", "Codigo de autenticacion incorrecto", status_code=401)

    user.mfa_enabled = True
    await audit_service.log(db, action="iam.mfa_enabled", actor_user_id=user.id)
    await db.commit()


async def disable_mfa(db: AsyncSession, *, user: User, code: str) -> None:
    if not user.mfa_secret or not pyotp.TOTP(user.mfa_secret).verify(code, valid_window=1):
        raise AppError("INVALID_MFA_CODE", "Codigo de autenticacion incorrecto", status_code=401)

    role_codes = await _user_role_codes(db, user_id=user.id)
    if any(not rules.can_disable_mfa(code) for code in role_codes):
        raise AppError(
            "MFA_REQUIRED", "Tu rol exige MFA activo y no se puede desactivar", status_code=403
        )

    user.mfa_enabled = False
    user.mfa_secret = None
    await audit_service.log(db, action="iam.mfa_disabled", actor_user_id=user.id)
    await db.commit()


async def list_clinic_users(db: AsyncSession, *, clinic_id: uuid.UUID) -> list[tuple[User, Role]]:
    stmt = (
        select(User, Role)
        .join(UserClinic, UserClinic.user_id == User.id)
        .join(Role, Role.id == UserClinic.role_id)
        .where(UserClinic.clinic_id == clinic_id)
        .order_by(User.full_name)
    )
    return [(user, role) for user, role in (await db.execute(stmt)).all()]


async def create_clinic_user(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    data: UserCreateRequest,
    created_by: uuid.UUID,
) -> tuple[User, Role]:
    if data.role_code not in rules.ROLE_CODES:
        raise AppError("INVALID_ROLE", "Rol desconocido", status_code=400)

    role = (await db.execute(select(Role).where(Role.code == data.role_code))).scalar_one_or_none()
    if role is None:
        raise AppError("INVALID_ROLE", "Rol no configurado en el catalogo", status_code=400)

    existing = (await db.execute(select(User).where(User.email == data.email))).scalar_one_or_none()
    if existing is not None:
        raise AppError("EMAIL_TAKEN", "Ya existe un usuario con ese correo", status_code=409)

    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        created_by=created_by,
    )
    db.add(user)
    await db.flush()

    membership = UserClinic(
        user_id=user.id, clinic_id=clinic_id, role_id=role.id, created_by=created_by
    )
    db.add(membership)

    await audit_service.log(
        db,
        action="iam.user_created",
        actor_user_id=created_by,
        clinic_id=clinic_id,
        entity_type="user",
        entity_id=str(user.id),
        details={"role": role.code},
    )
    await db.commit()
    return user, role


async def update_clinic_user(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    data: UserUpdateRequest,
    updated_by: uuid.UUID,
) -> tuple[User, Role]:
    stmt = select(UserClinic).where(
        UserClinic.clinic_id == clinic_id, UserClinic.user_id == user_id
    )
    membership = (await db.execute(stmt)).scalar_one_or_none()
    if membership is None:
        raise AppError("NOT_FOUND", "El usuario no pertenece a esta clinica", status_code=404)

    user = await db.get(User, user_id)
    assert user is not None

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.role_code is not None:
        if data.role_code not in rules.ROLE_CODES:
            raise AppError("INVALID_ROLE", "Rol desconocido", status_code=400)
        role = (
            await db.execute(select(Role).where(Role.code == data.role_code))
        ).scalar_one_or_none()
        if role is None:
            raise AppError("INVALID_ROLE", "Rol no configurado en el catalogo", status_code=400)
        membership.role_id = role.id

    await audit_service.log(
        db,
        action="iam.user_updated",
        actor_user_id=updated_by,
        clinic_id=clinic_id,
        entity_type="user",
        entity_id=str(user.id),
    )
    await db.commit()

    role = await db.get(Role, membership.role_id)
    assert role is not None
    return user, role
