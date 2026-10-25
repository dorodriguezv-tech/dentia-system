import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import AuditedMixin, Base, UUIDPkMixin
from app.modules.iam.rules import DEFAULT_CLINIC_TIMEZONE


class Organization(AuditedMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200))

    clinics: Mapped[list["Clinic"]] = relationship(back_populates="organization")


class Clinic(AuditedMixin, Base):
    __tablename__ = "clinics"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Contador para el numero de expediente de pacientes (modulo patients, Fase 3).
    next_patient_number: Mapped[int] = mapped_column(Integer, default=1)
    # Nombre de zona horaria IANA (bug #42 de docs/PENDIENTES_CLINICOS.md): de
    # que dia es "hoy" para citas/atenciones (columnas TIMESTAMPTZ en UTC) se
    # calcula con ESTA zona, nunca con la hora local del servidor.
    timezone: Mapped[str] = mapped_column(
        String(50), default=DEFAULT_CLINIC_TIMEZONE, server_default=DEFAULT_CLINIC_TIMEZONE
    )

    organization: Mapped[Organization] = relationship(back_populates="clinics")


class Role(UUIDPkMixin, Base):
    __tablename__ = "roles"

    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Permission(UUIDPkMixin, Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )


class User(AuditedMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    # Obligatoria al dar de alta un odontologo/especialista (agenda_rules.PROVIDER_ROLES
    # -- ver iam/service.py::create_clinic_user); se usa en documentos firmados
    # (plantillas de consentimiento) para identificar a quien atiende.
    professional_license: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    # Politica de contrasenas (sec. 6, cambio #1): hashes de las ultimas
    # PASSWORD_HISTORY_SIZE contrasenas (sin contar la actual), mas vieja
    # primero -- para que un cambio de contrasena pueda rechazar reutilizar
    # alguna reciente. Nunca contrasenas en claro.
    password_history: Mapped[list[str]] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Cuenta de demostracion de tiempo limitado (rol "demo", ver
    # permissions_catalog.py): expires_at bloquea el login solo (no hace falta un
    # job periodico) en cuanto pase la fecha -- ver iam/service.py::login.
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # is_sandboxed: sus acciones administrativas sensibles (borrar/editar otro
    # usuario) quedan visibles en la UI pero no se ejecutan de verdad -- ver
    # iam/service.py::delete_user/update_clinic_user. Su propia sucursal, por
    # separado, se reinicia a un estado de ejemplo en cada login/logout
    # (reset_demo_clinic), asi que el resto de sus acciones si "funcionan" dentro
    # de esa sucursal, pero nunca sobreviven a la siguiente sesion.
    is_sandboxed: Mapped[bool] = mapped_column(Boolean, default=False)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    @property
    def has_photo(self) -> bool:
        return self.photo_path is not None


class UserClinic(AuditedMixin, Base):
    __tablename__ = "user_clinics"
    __table_args__ = (UniqueConstraint("user_id", "clinic_id", name="uq_user_clinic"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("roles.id", ondelete="RESTRICT")
    )

    user: Mapped[User] = relationship(foreign_keys=[user_id])
    clinic: Mapped[Clinic] = relationship()
    role: Mapped[Role] = relationship()


class UserPreference(AuditedMixin, Base):
    """B7 (docs/06_APP_MOVIL_V1_1_PARIDAD.md sec. 4): preferencias personales del
    usuario (idioma, voz y velocidad de Dentia, tema, tiempo de bloqueo), para que
    viajen entre web, tablet y telefono en vez de vivir solo en un dispositivo. No
    son datos clinicos, por eso no llevan clinic_id (CLAUDE.md sec. 6: "cuando
    aplique")."""

    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    language: Mapped[str] = mapped_column(String(10), default="es-MX", server_default="es-MX")
    theme: Mapped[str] = mapped_column(String(10), default="system", server_default="system")
    dentia_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    voice_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    speech_rate: Mapped[float] = mapped_column(Float, default=1.0, server_default="1.0")
    speech_volume: Mapped[float] = mapped_column(Float, default=1.0, server_default="1.0")
    lock_timeout_minutes: Mapped[int] = mapped_column(Integer, default=2, server_default="2")


class RefreshToken(UUIDPkMixin, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("refresh_tokens.id", ondelete="SET NULL"), nullable=True
    )
