import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import AuditedMixin, Base
from app.modules.patients.rules import DEFAULT_STATUS


class Patient(AuditedMixin, Base):
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("clinic_id", "expediente_number", name="uq_patient_expediente_per_clinic"),
    )
    # Ademas existe el indice GIN "ix_patients_full_name_trgm" sobre
    # immutable_unaccent(lower(full_name)) para la busqueda tolerante a errores (ver
    # migracion 0079b0a977a3). No se declara aqui como Index() porque depende de la
    # funcion SQL immutable_unaccent (creada con DDL crudo, no mapeable como columna de
    # SQLAlchemy); por eso cada `alembic revision --autogenerate` lo marcara como
    # "a eliminar" aunque siga existiendo — hay que quitar esa linea a mano antes de
    # aplicar la migracion generada.

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    expediente_number: Mapped[str] = mapped_column(String(20))

    first_name: Mapped[str] = mapped_column(String(100))
    last_name_paternal: Mapped[str] = mapped_column(String(100))
    last_name_maternal: Mapped[str | None] = mapped_column(String(100), nullable=True)
    full_name: Mapped[str] = mapped_column(String(300))

    date_of_birth: Mapped[date] = mapped_column(Date)
    sex: Mapped[str | None] = mapped_column(String(1), nullable=True)

    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(String(300), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default=DEFAULT_STATUS)
    photo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Anotacion del expediente (pendiente #73 de docs/PENDIENTES_CLINICOS.md):
    # "pediatrico"/"adulto". Nullable y editable a mano -- patients/service.py
    # la calcula a partir de date_of_birth solo cuando no viene explicita en el
    # payload de alta/edicion; si el usuario la especifica, no se recalcula
    # despues aunque la fecha de nacimiento ya este registrada de otra forma.
    patient_type: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Fase A (rediseno del expediente segun formatos oficiales, docs/clinica):
    # campos compartidos que hoy pide la Historia Clinica General y que antes no
    # existian en el paciente. Todos opcionales (nullable) para no romper pacientes
    # ya dados de alta. education_level/marital_status/religion/ethnic_group/race
    # son texto libre por ahora (sin catalogo administrable todavia): se documentan
    # como pendientes de validar con la clinica en docs/PENDIENTES_CLINICOS.md,
    # igual que otros catalogos provisionales del proyecto.
    birth_place: Mapped[str | None] = mapped_column(String(200), nullable=True)
    blood_type: Mapped[str | None] = mapped_column(String(5), nullable=True)
    education_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    can_read_write: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    religion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ethnic_group: Mapped[str | None] = mapped_column(String(100), nullable=True)
    race: Mapped[str | None] = mapped_column(String(100), nullable=True)
    occupation: Mapped[str | None] = mapped_column(String(150), nullable=True)
    marital_status: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # B3 (Parte B, Fase 12.2): gabinete y profesional tratante por defecto -- la
    # agenda los preselecciona al agendar una cita para este paciente (opcionales,
    # un paciente nuevo no tiene por que tener ya un profesional asignado).
    default_resource_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("resources.id", ondelete="SET NULL"), nullable=True
    )
    primary_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("providers.id", ondelete="SET NULL"), nullable=True
    )


class PatientContact(AuditedMixin, Base):
    __tablename__ = "patient_contacts"

    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(20))
    full_name: Mapped[str] = mapped_column(String(200))
    relationship_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Pacientes pediatricos (CLAUDE.md, alta asistida): la ocupacion relevante para un
    # menor es la del tutor/responsable, no la del paciente -- por eso vive aqui y no en
    # Patient.occupation (que se oculta en el formulario cuando el paciente es pediatrico).
    occupation: Mapped[str | None] = mapped_column(String(150), nullable=True)
