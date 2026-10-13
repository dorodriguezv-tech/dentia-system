import uuid
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.validators import Email
from app.modules.iam.rules import is_valid_timezone

PreferenceTheme = Literal["system", "light", "dark"]


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
    timezone: str

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
    # Bug #42 de docs/PENDIENTES_CLINICOS.md: "hoy" para citas/atenciones debe
    # calcularse con la zona horaria de la sucursal, no la del servidor.
    timezone: str | None = Field(default=None, max_length=50)

    @field_validator("timezone")
    @classmethod
    def _valid_iana_timezone(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_timezone(value):
            raise ValueError(
                "Zona horaria invalida (debe ser un nombre IANA, p. ej. America/Mexico_City)"
            )
        return value


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
    # B4 (docs/05_APP_MOVIL.md Sec. 7): la app movil oculta botones segun el permiso,
    # pero el backend sigue siendo quien autoriza cada peticion. Campos planos
    # agregados sin tocar `clinic`/`role` (el frontend web ya los usa anidados).
    clinic_name: str
    permissions: list[str]


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


class UserPreferencesOut(BaseModel):
    """B7 (docs/06_APP_MOVIL_V1_1_PARIDAD.md sec. 4)."""

    language: str
    theme: PreferenceTheme
    dentia_enabled: bool
    voice_id: str | None
    speech_rate: float
    speech_volume: float
    lock_timeout_minutes: int

    model_config = {"from_attributes": True}


class UserPreferencesUpdateRequest(BaseModel):
    """Actualizacion parcial: un campo en None significa "no lo toques", no "bórralo"
    (mismo criterio que ClinicUpdateRequest/UserUpdateRequest en este modulo)."""

    language: str | None = Field(default=None, min_length=2, max_length=10)
    theme: PreferenceTheme | None = None
    dentia_enabled: bool | None = None
    voice_id: str | None = Field(default=None, max_length=200)
    speech_rate: float | None = Field(default=None, ge=0.5, le=2.0)
    speech_volume: float | None = Field(default=None, ge=0.0, le=1.0)
    lock_timeout_minutes: int | None = Field(default=None, ge=1, le=30)
