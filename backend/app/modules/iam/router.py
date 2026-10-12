import uuid

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_clinic_id, get_current_user, require_permission
from app.modules.iam import service
from app.modules.iam.models import User
from app.modules.iam.schemas import (
    ClinicOut,
    ClinicUpdateRequest,
    LoginMfaRequest,
    LoginRequest,
    LogoutRequest,
    MfaCodeRequest,
    MfaRequiredResponse,
    MfaSetupResponse,
    MyClinicOut,
    RefreshRequest,
    TokenResponse,
    UserCreateRequest,
    UserOut,
    UserUpdateRequest,
    UserWithRoleOut,
)

router = APIRouter(tags=["iam"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _user_out(db: AsyncSession, user: User) -> UserOut:
    out = UserOut.model_validate(user)
    out.mfa_setup_required = await service.mfa_setup_required(db, user=user)
    return out


async def _token_response(
    db: AsyncSession, user: User, tokens: tuple[str, str, int]
) -> TokenResponse:
    access_token, refresh_token, expires_in = tokens
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=await _user_out(db, user),
    )


@router.post("/auth/login", response_model=TokenResponse | MfaRequiredResponse)
async def login(
    payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenResponse | MfaRequiredResponse:
    user, mfa_token, tokens = await service.login(
        db, email=payload.email, password=payload.password, ip_address=_client_ip(request)
    )
    if mfa_token is not None:
        return MfaRequiredResponse(mfa_token=mfa_token)
    assert user is not None and tokens is not None
    return await _token_response(db, user, tokens)


@router.post("/auth/login/mfa", response_model=TokenResponse)
async def login_mfa(
    payload: LoginMfaRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    user, tokens = await service.login_with_mfa(
        db, mfa_token=payload.mfa_token, code=payload.code, ip_address=_client_ip(request)
    )
    return await _token_response(db, user, tokens)


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user, tokens = await service.refresh_tokens(db, refresh_token=payload.refresh_token)
    return await _token_response(db, user, tokens)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: LogoutRequest, db: AsyncSession = Depends(get_db)) -> None:
    await service.logout(db, refresh_token=payload.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> UserOut:
    return await _user_out(db, current_user)


@router.get("/me/clinics", response_model=list[MyClinicOut])
async def my_clinics(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[MyClinicOut]:
    triples = await service.get_my_clinics(db, user_id=current_user.id)
    return [
        MyClinicOut(clinic=clinic, role=role, clinic_name=clinic.name, permissions=permissions)
        for clinic, role, permissions in triples
    ]


@router.patch("/clinics/current", response_model=ClinicOut)
async def update_current_clinic(
    payload: ClinicUpdateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("catalogs.manage")),
    db: AsyncSession = Depends(get_db),
) -> ClinicOut:
    clinic = await service.update_current_clinic(
        db, clinic_id=clinic_id, data=payload, actor_id=actor.id
    )
    return ClinicOut.model_validate(clinic)


@router.post("/auth/mfa/setup", response_model=MfaSetupResponse)
async def mfa_setup(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> MfaSetupResponse:
    secret, otpauth_url = await service.setup_mfa(db, user=current_user)
    return MfaSetupResponse(secret=secret, otpauth_url=otpauth_url)


@router.post("/auth/mfa/enable", status_code=status.HTTP_204_NO_CONTENT)
async def mfa_enable(
    payload: MfaCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.enable_mfa(db, user=current_user, code=payload.code)


@router.post("/auth/mfa/disable", status_code=status.HTTP_204_NO_CONTENT)
async def mfa_disable(
    payload: MfaCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await service.disable_mfa(db, user=current_user, code=payload.code)


@router.get("/users", response_model=list[UserWithRoleOut])
async def list_users(
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("iam.view_users")),
    db: AsyncSession = Depends(get_db),
) -> list[UserWithRoleOut]:
    pairs = await service.list_clinic_users(db, clinic_id=clinic_id)
    return [UserWithRoleOut(user=user, role=role) for user, role in pairs]


@router.post("/users", response_model=UserWithRoleOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("iam.manage_users")),
    db: AsyncSession = Depends(get_db),
) -> UserWithRoleOut:
    user, role = await service.create_clinic_user(
        db, clinic_id=clinic_id, data=payload, created_by=actor.id
    )
    return UserWithRoleOut(user=user, role=role)


@router.patch("/users/{user_id}", response_model=UserWithRoleOut)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdateRequest,
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("iam.manage_users")),
    db: AsyncSession = Depends(get_db),
) -> UserWithRoleOut:
    user, role = await service.update_clinic_user(
        db, clinic_id=clinic_id, user_id=user_id, data=payload, updated_by=actor.id
    )
    return UserWithRoleOut(user=user, role=role)
