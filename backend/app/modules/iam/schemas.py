import uuid

from pydantic import BaseModel, Field

from app.core.validators import Email


class LoginRequest(BaseModel):
    email: Email
    password: str


class LoginMfaRequest(BaseModel):
    mfa_token: str
    code: str = Field(min_length=6, max_length=6)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ClinicOut(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class RoleOut(BaseModel):
    code: str
    name: str

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: uuid.UUID
    email: Email
    full_name: str
    is_active: bool
    mfa_enabled: bool
    mfa_setup_required: bool = False

    model_config = {"from_attributes": True}


class MfaRequiredResponse(BaseModel):
    mfa_required: bool = True
    mfa_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class MyClinicOut(BaseModel):
    clinic: ClinicOut
    role: RoleOut


class MfaSetupResponse(BaseModel):
    secret: str
    otpauth_url: str


class MfaCodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=6)


class UserCreateRequest(BaseModel):
    email: Email
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    role_code: str


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    is_active: bool | None = None
    role_code: str | None = None


class UserWithRoleOut(BaseModel):
    user: UserOut
    role: RoleOut
