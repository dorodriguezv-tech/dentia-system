import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
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
