import uuid

from sqlalchemy import Boolean, ForeignKey, Index, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import AuditedMixin, Base


class ToothFinding(AuditedMixin, Base):
    """Evento del odontograma (regla 5 de CLAUDE.md): nunca se sobrescribe. Un hallazgo
    nuevo para la misma pieza/superficie/tipo marca is_current=False en el anterior y
    apunta a el via supersedes_id; el historial completo queda intacto."""

    __tablename__ = "tooth_findings"

    clinic_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clinics.id", ondelete="CASCADE")
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE")
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("encounters.id", ondelete="RESTRICT")
    )
    tooth_fdi: Mapped[int] = mapped_column(SmallInteger)
    surface: Mapped[str | None] = mapped_column(String(1), nullable=True)
    finding_code: Mapped[str] = mapped_column(String(40))
    kind: Mapped[str] = mapped_column(String(10))
    material: Mapped[str | None] = mapped_column(String(100), nullable=True)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tooth_findings.id", ondelete="SET NULL"), nullable=True
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    origin: Mapped[str] = mapped_column(String(15), default="MANUAL")


# Indice unico parcial (regla 5): solo un hallazgo vigente por (paciente, pieza,
# superficie, tipo). COALESCE trata "toda la pieza" (surface NULL) como un valor
# concreto para la comparacion, porque Postgres no considera iguales dos NULL en un
# indice unico por defecto.
Index(
    "ux_tooth_findings_current",
    ToothFinding.patient_id,
    ToothFinding.tooth_fdi,
    func.coalesce(ToothFinding.surface, ""),
    ToothFinding.kind,
    unique=True,
    postgresql_where=ToothFinding.is_current.is_(True),
)
