import uuid
from datetime import UTC, datetime, timedelta

import pyotp
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit_service
from app.audit.models import AuditEvent
from app.core.captcha import verify_turnstile
from app.core.config import get_settings
from app.core.deps import user_has_any_permission
from app.core.errors import AppError
from app.core.password_policy import PASSWORD_HISTORY_SIZE
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
from app.modules.agenda import rules as agenda_rules
from app.modules.agenda import service as agenda_service
from app.modules.iam import rules
from app.modules.iam.demo_sandbox import reset_demo_clinic
from app.modules.iam.models import (
    Clinic,
    Permission,
    RefreshToken,
    Role,
    RolePermission,
    User,
    UserClinic,
    UserPreference,
)
from app.modules.iam.schemas import (
    ClinicUpdateRequest,
    UserCreateRequest,
    UserPreferencesUpdateRequest,
    UserUpdateRequest,
)

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
    db: AsyncSession,
    *,
    email: str,
    password: str,
    ip_address: str | None,
    turnstile_token: str | None = None,
) -> tuple[User | None, str | None, tuple[str, str, int] | None]:
    """Devuelve (user, mfa_token, tokens). Si mfa_token no es None, falta el paso MFA."""

    # Captcha antes que cualquier otra cosa: no revela ni el conteo de intentos
    # fallidos ni si el correo existe a una peticion que no lo supera.
    if not await verify_turnstile(turnstile_token, remote_ip=ip_address):
        raise AppError(
            "CAPTCHA_INVALID", "Verificacion de seguridad invalida o expirada.", status_code=400
        )

    if await _recent_login_failures(db, email) >= rules.MAX_LOGIN_FAILURES:
        raise AppError(
            "RATE_LIMITED",
            "Demasiados intentos fallidos. Intenta de nuevo mas tarde.",
            status_code=429,
        )

    stmt = select(User).where(User.email == email)
    user = (await db.execute(stmt)).scalar_one_or_none()

    # Cuentas de demostracion de tiempo limitado (User.expires_at, p.ej. "demo"):
    # se desactivan solas en cuanto alguien intenta entrar despues de su fecha
    # limite -- sin job periodico, el login es el unico punto de entrada posible.
    user_expired = (
        user is not None and user.expires_at is not None and datetime.now(UTC) >= user.expires_at
    )
    if user is not None and user.is_active and user_expired:
        user.is_active = False
        await db.flush()

    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        await audit_service.log(
            db,
            action="auth.login_failed",
            details={"email": email},
            ip_address=ip_address,
        )
        await db.commit()
        raise AppError("INVALID_CREDENTIALS", "Correo o contrasena incorrectos", status_code=401)

    if user.mfa_enabled and rules.MFA_ENABLED:
        await db.commit()
        return user, create_mfa_token(user.id), None

    if user.is_sandboxed:
        user_id = user.id
        clinic_id = (
            await db.execute(select(UserClinic.clinic_id).where(UserClinic.user_id == user_id))
        ).scalar_one()
        await reset_demo_clinic(db, clinic_id=clinic_id, demo_user_id=user_id)
        # reset_demo_clinic hace varios commit() propios -- con expire_on_commit
        # (default de SQLAlchemy), eso deja "user" expirado; se vuelve a pedir en
        # vez de dejar que una lectura implicita de sus atributos dispare una
        # recarga a mitad de una conexion que el pool ya dio por terminada.
        refreshed_user = await db.get(User, user_id)
        assert refreshed_user is not None
        user = refreshed_user

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

        # Respaldo del reinicio que ya ocurre en el siguiente login (sec.
        # reset_demo_clinic): limpia de inmediato si el cierre de sesion si
        # ocurrio limpio, en vez de dejar el contenido de ejemplo visible
        # hasta que alguien mas vuelva a entrar.
        user = await db.get(User, row.user_id)
        if user is not None and user.is_sandboxed:
            clinic_id = (
                await db.execute(select(UserClinic.clinic_id).where(UserClinic.user_id == user.id))
            ).scalar_one()
            await reset_demo_clinic(db, clinic_id=clinic_id, demo_user_id=user.id)


async def change_password(
    db: AsyncSession, *, user: User, current_password: str, new_password: str
) -> None:
    """Autoservicio (sec. 6, cambio #1): sin esto un usuario jamas podria dejar
    de usar la contrasena inicial compartida del alta controlada
    (bootstrap_clinic.py). Rechaza reutilizar la contrasena actual o
    cualquiera de las ultimas PASSWORD_HISTORY_SIZE, y revoca las sesiones
    existentes -- una sesion robada no debe sobrevivir a un cambio de
    contrasena."""
    if not verify_password(current_password, user.hashed_password):
        raise AppError("INVALID_CREDENTIALS", "Contrasena actual incorrecta", status_code=401)

    if verify_password(new_password, user.hashed_password) or any(
        verify_password(new_password, old_hash) for old_hash in user.password_history
    ):
        raise AppError(
            "PASSWORD_REUSED",
            f"No se puede reutilizar ninguna de las ultimas {PASSWORD_HISTORY_SIZE} contrasenas.",
            status_code=400,
        )

    history = [*user.password_history, user.hashed_password][-PASSWORD_HISTORY_SIZE:]
    user.password_history = history
    user.hashed_password = hash_password(new_password)

    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await audit_service.log(db, action="auth.password_changed", actor_user_id=user.id)
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


async def get_my_clinics(
    db: AsyncSession, *, user_id: uuid.UUID
) -> list[tuple[Clinic, Role, list[str]]]:
    stmt = (
        select(Clinic, Role)
        .join(UserClinic, UserClinic.clinic_id == Clinic.id)
        .join(Role, Role.id == UserClinic.role_id)
        .where(UserClinic.user_id == user_id)
        .order_by(Clinic.name)
    )
    pairs = [(clinic, role) for clinic, role in (await db.execute(stmt)).all()]

    role_ids = {role.id for _clinic, role in pairs}
    permissions_by_role = await _permission_codes_by_role(db, role_ids=role_ids)
    return [
        (clinic, role, sorted(permissions_by_role.get(role.id, set()))) for clinic, role in pairs
    ]


async def _permission_codes_by_role(
    db: AsyncSession, *, role_ids: set[uuid.UUID]
) -> dict[uuid.UUID, set[str]]:
    if not role_ids:
        return {}
    stmt = (
        select(RolePermission.role_id, Permission.code)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(RolePermission.role_id.in_(role_ids))
    )
    result: dict[uuid.UUID, set[str]] = {role_id: set() for role_id in role_ids}
    for role_id, code in (await db.execute(stmt)).all():
        result[role_id].add(code)
    return result


async def update_current_clinic(
    db: AsyncSession, *, clinic_id: uuid.UUID, data: ClinicUpdateRequest, actor_id: uuid.UUID
) -> Clinic:
    """Pendiente de B1 (Parte B, Fase 12.2): editar nombre/direccion/telefono de la
    propia sucursal. Siempre la de `clinic_id` (X-Clinic-Id) -- nunca recibe un id
    por la URL, asi que no hay forma de editar una sucursal ajena desde aqui."""
    clinic = await db.get(Clinic, clinic_id)
    if clinic is None:
        raise AppError("NOT_FOUND", "Sucursal no encontrada", status_code=404)

    if data.name is not None:
        clinic.name = data.name
    if data.address is not None:
        clinic.address = data.address
    if data.phone is not None:
        clinic.phone = data.phone
    if data.timezone is not None:
        clinic.timezone = data.timezone

    await audit_service.log(
        db,
        action="iam.clinic_updated",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="clinic",
        entity_id=str(clinic.id),
    )
    await db.commit()
    return clinic


async def get_preferences(db: AsyncSession, *, user_id: uuid.UUID) -> UserPreference:
    """B7: crea la fila con los valores por defecto la primera vez que se consulta,
    para no tener que sincronizar un alta en el registro del usuario."""
    stmt = select(UserPreference).where(UserPreference.user_id == user_id)
    pref = (await db.execute(stmt)).scalar_one_or_none()
    if pref is None:
        pref = UserPreference(user_id=user_id, created_by=user_id)
        db.add(pref)
        await db.commit()
    return pref


async def update_preferences(
    db: AsyncSession, *, user_id: uuid.UUID, data: UserPreferencesUpdateRequest
) -> UserPreference:
    pref = await get_preferences(db, user_id=user_id)

    if data.language is not None:
        pref.language = data.language
    if data.theme is not None:
        pref.theme = data.theme
    if data.dentia_enabled is not None:
        pref.dentia_enabled = data.dentia_enabled
    if data.voice_id is not None:
        pref.voice_id = data.voice_id
    if data.speech_rate is not None:
        pref.speech_rate = data.speech_rate
    if data.speech_volume is not None:
        pref.speech_volume = data.speech_volume
    if data.lock_timeout_minutes is not None:
        pref.lock_timeout_minutes = data.lock_timeout_minutes

    await audit_service.log(
        db,
        action="iam.preferences_updated",
        actor_user_id=user_id,
        entity_type="user_preference",
        entity_id=str(pref.id),
    )
    await db.commit()
    return pref


async def setup_mfa(db: AsyncSession, *, user: User) -> tuple[str, str]:
    secret = pyotp.random_base32()
    user.mfa_secret = secret
    await db.commit()
    otpauth_url = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="DENT-IA")
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

    # Un odontologo/especialista siempre atiende pacientes y firma documentos a su
    # nombre (plantillas de consentimiento) -- su cedula profesional es obligatoria
    # desde el alta, no un dato que se pueda completar "despues".
    if role.code in agenda_rules.PROVIDER_ROLES and not (data.professional_license or "").strip():
        raise AppError(
            "VALIDATION_ERROR",
            "La cedula profesional es obligatoria para odontologos y especialistas",
            status_code=422,
        )

    existing = (await db.execute(select(User).where(User.email == data.email))).scalar_one_or_none()
    if existing is not None:
        raise AppError("EMAIL_TAKEN", "Ya existe un usuario con ese correo", status_code=409)

    user = User(
        email=data.email,
        full_name=data.full_name,
        professional_license=(data.professional_license or "").strip() or None,
        hashed_password=hash_password(data.password),
        created_by=created_by,
    )
    db.add(user)
    await db.flush()

    membership = UserClinic(
        user_id=user.id, clinic_id=clinic_id, role_id=role.id, created_by=created_by
    )
    db.add(membership)

    # A1: un odontologo/especialista nuevo debe aparecer de inmediato en la agenda,
    # sin que el administrador tenga que crear su Provider a mano por separado.
    if role.code in agenda_rules.PROVIDER_ROLES:
        provider = await agenda_service.ensure_provider_for_user(
            db, clinic_id=clinic_id, user_id=user.id, actor_id=created_by
        )
        # B2 (Parte B, Fase 12.2): gabinete por defecto en esta sucursal.
        await agenda_service.set_provider_default_resource(
            db, clinic_id=clinic_id, provider=provider, resource_id=data.default_resource_id
        )

    assigned_clinic_ids = [clinic_id]
    seen_additional: set[uuid.UUID] = set()
    for assignment in data.additional_clinics:
        if assignment.clinic_id == clinic_id or assignment.clinic_id in seen_additional:
            raise AppError(
                "DUPLICATE_CLINIC",
                "Cada sucursal solo se puede elegir una vez",
                status_code=400,
            )
        seen_additional.add(assignment.clinic_id)

        # B2: el administrador solo puede asignar a sucursales donde el mismo tiene
        # `iam.manage_users` -- igual que si llamara este endpoint con esa sucursal
        # activa (X-Clinic-Id), no se le da acceso a sucursales ajenas por aqui.
        allowed = await user_has_any_permission(
            db, user_id=created_by, clinic_id=assignment.clinic_id, codes=("iam.manage_users",)
        )
        if not allowed:
            raise AppError(
                "FORBIDDEN",
                "No tienes permiso para asignar usuarios en una de las sucursales elegidas",
                status_code=403,
            )

        extra_clinic = await db.get(Clinic, assignment.clinic_id)
        if extra_clinic is None:
            raise AppError("NOT_FOUND", "Sucursal no encontrada", status_code=404)

        db.add(
            UserClinic(
                user_id=user.id,
                clinic_id=assignment.clinic_id,
                role_id=role.id,
                created_by=created_by,
            )
        )
        if role.code in agenda_rules.PROVIDER_ROLES:
            extra_provider = await agenda_service.ensure_provider_for_user(
                db, clinic_id=assignment.clinic_id, user_id=user.id, actor_id=created_by
            )
            await agenda_service.set_provider_default_resource(
                db,
                clinic_id=assignment.clinic_id,
                provider=extra_provider,
                resource_id=assignment.default_resource_id,
            )
        assigned_clinic_ids.append(assignment.clinic_id)

    await audit_service.log(
        db,
        action="iam.user_created",
        actor_user_id=created_by,
        clinic_id=clinic_id,
        entity_type="user",
        entity_id=str(user.id),
        details={"role": role.code, "clinic_ids": [str(c) for c in assigned_clinic_ids]},
    )
    await db.commit()
    return user, role


async def update_clinic_user(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    user_id: uuid.UUID,
    data: UserUpdateRequest,
    actor: User,
) -> tuple[User, Role]:
    stmt = select(UserClinic).where(
        UserClinic.clinic_id == clinic_id, UserClinic.user_id == user_id
    )
    membership = (await db.execute(stmt)).scalar_one_or_none()
    if membership is None:
        raise AppError("NOT_FOUND", "El usuario no pertenece a esta clinica", status_code=404)

    user = await db.get(User, user_id)
    assert user is not None
    updated_by = actor.id

    # Cuenta de demostracion (is_sandboxed): editar a otro usuario queda visible
    # en la pantalla y "funciona" a los ojos de quien la usa, pero no debe
    # cambiar nada de verdad -- se devuelve el usuario tal cual esta.
    if actor.is_sandboxed:
        role = await db.get(Role, membership.role_id)
        assert role is not None
        return user, role

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.professional_license is not None:
        user.professional_license = data.professional_license.strip() or None
    if data.new_password is not None:
        user.hashed_password = hash_password(data.new_password)
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

    role = await db.get(Role, membership.role_id)
    assert role is not None

    # A1: mantener el Provider sincronizado con el rol/estado final del usuario, sin
    # importar si este llamado cambio el rol, el estado activo, o ambos -- idempotente.
    if role.code in agenda_rules.PROVIDER_ROLES and user.is_active:
        await agenda_service.ensure_provider_for_user(
            db, clinic_id=clinic_id, user_id=user.id, actor_id=updated_by
        )
    else:
        await agenda_service.set_provider_active_for_user(
            db, clinic_id=clinic_id, user_id=user.id, is_active=False
        )

    await audit_service.log(
        db,
        action="iam.user_updated",
        actor_user_id=updated_by,
        clinic_id=clinic_id,
        entity_type="user",
        entity_id=str(user.id),
    )
    await db.commit()

    return user, role


async def delete_user(
    db: AsyncSession, *, clinic_id: uuid.UUID, user_id: uuid.UUID, actor: User
) -> None:
    """Borrado real (no es contenido clinico -- regla 2 de CLAUDE.md no aplica a
    usuarios): si el usuario tiene historial asociado (citas, notas, planes...),
    la base de datos lo rechaza (llaves foraneas RESTRICT) y se traduce a un
    error claro en vez de dejarlo a medias. Si solo pertenece a esta sucursal,
    se borra la cuenta completa; si pertenece a varias, solo se le quita esta."""
    if actor.is_sandboxed:
        return  # visible en la UI, pero no hace nada de verdad (cuenta de demo)

    if user_id == actor.id:
        raise AppError("CANNOT_DELETE_SELF", "No puedes borrar tu propia cuenta", status_code=400)

    membership = (
        await db.execute(
            select(UserClinic).where(
                UserClinic.clinic_id == clinic_id, UserClinic.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise AppError("NOT_FOUND", "El usuario no pertenece a esta clinica", status_code=404)

    await db.delete(membership)
    await db.flush()

    remaining = (
        await db.execute(
            select(func.count()).select_from(UserClinic).where(UserClinic.user_id == user_id)
        )
    ).scalar_one()

    if remaining == 0:
        user = await db.get(User, user_id)
        if user is not None:
            try:
                await db.delete(user)
                await db.flush()
            except IntegrityError as exc:
                await db.rollback()
                raise AppError(
                    "USER_HAS_HISTORY",
                    "No se puede borrar: tiene historial asociado (citas, notas, planes de "
                    "tratamiento...). Desactivalo en su lugar.",
                    status_code=409,
                ) from exc

    await audit_service.log(
        db,
        action="iam.user_deleted",
        actor_user_id=actor.id,
        clinic_id=clinic_id,
        entity_type="user",
        entity_id=str(user_id),
    )
    await db.commit()
