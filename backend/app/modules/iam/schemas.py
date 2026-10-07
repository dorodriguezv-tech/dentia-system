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
    address: str | None = None
    phone: str | None = None

    model_config = {"from_attributes": True}


class ClinicUpdateRequest(BaseModel):
    """Pendiente de B1 (Parte B, Fase 12.2): editar los datos basicos (no
    clinicos) de la propia sucursal desde Configuracion -> Catalogos. A
    proposito separado de `iam.manage_clinics` (solo superadmin, crear/administrar
    sucursales entre organizaciones, CLAUDE.md sec. 5): esto es `catalogs.manage`
    (admin_clinica) editando los datos de contacto de SU PROPIA sucursal, nunca
    la de otra ni creando una nueva."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    address: str | None = Field(default=None, max_length=300)
    phone: str | None = Field(default=None, max_length=30)


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


class ClinicAssignmentRequest(BaseModel):
    """B2 (Parte B, Fase 12.2): una sucursal adicional a la que se asigna el usuario
    nuevo, cada una con su propio gabinete por defecto (ver UserCreateRequest)."""

    clinic_id: uuid.UUID
    default_resource_id: uuid.UUID | None = None


class UserCreateRequest(BaseModel):
    email: Email
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    role_code: str
    # B2: gabinete por defecto en la sucursal activa (X-Clinic-Id) mas, si el
    # administrador elige mas de una sucursal, una asignacion por cada una extra --
    # el mismo rol en todas, el formulario no ofrece elegir un rol distinto por
    # sucursal.
    default_resource_id: uuid.UUID | None = None
    additional_clinics: list[ClinicAssignmentRequest] = Field(default_factory=list)


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    is_active: bool | None = None
    role_code: str | None = None


class UserWithRoleOut(BaseModel):
    user: UserOut
    role: RoleOut
