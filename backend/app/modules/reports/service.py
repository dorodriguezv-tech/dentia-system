import csv
import io
import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import AiSuggestion
from app.audit import service as audit_service
from app.core.config import get_settings
from app.modules.agenda.models import Appointment, Provider
from app.modules.billing import rules as billing_rules
from app.modules.billing import service as billing_service
from app.modules.billing.models import Charge
from app.modules.iam.models import Permission, Role, RolePermission, UserClinic
from app.modules.iam.models import User as IamUser
from app.modules.patients import rules as patients_rules
from app.modules.patients.models import Patient
from app.modules.reports import rules
from app.modules.reports.schemas import (
    AccountsReceivableOut,
    AccountsReceivableRow,
    AgendaDashboardSummary,
    AiUsageDashboardSummary,
    AiUsageReportOut,
    AiUsageReportRow,
    AppointmentReportRow,
    AppointmentsReportOut,
    BillingDashboardSummary,
    DashboardOut,
    PatientReportRow,
    PatientsDashboardSummary,
    PatientsReportOut,
    ProductionReportOut,
    ProductionReportRow,
    ProfessionalTotal,
    TreatmentDashboardSummary,
    TreatmentPlanReportRow,
    TreatmentPlansReportOut,
)
from app.modules.treatment.models import ProcedurePerformed, TreatmentPlan


def resolve_date_range(
    date_from: date | None, date_to: date | None, *, today: date | None = None
) -> tuple[date, date]:
    """Rango por defecto (catalogo configurable, CLAUDE.md sec. 7): ultimos 30 dias si
    no se especifica. Si ambos extremos vienen, solo se valida que no esten invertidos
    -- eso se hace en el router (AppError), esta funcion es pura para poder probarla."""
    reference = today or date.today()
    resolved_to = date_to or reference
    resolved_from = date_from or (resolved_to - timedelta(days=30))
    return resolved_from, resolved_to


def _date_bounds(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    start = datetime.combine(date_from, time.min, tzinfo=UTC)
    end_exclusive = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)
    return start, end_exclusive


# --------------------------------------------------------------------- 1. pacientes


async def build_patients_report(
    db: AsyncSession, *, clinic_id: uuid.UUID, date_from: date, date_to: date
) -> PatientsReportOut:
    start, end_exclusive = _date_bounds(date_from, date_to)

    new_stmt = select(func.count()).where(
        Patient.clinic_id == clinic_id,
        Patient.created_at >= start,
        Patient.created_at < end_exclusive,
    )
    new_patients = (await db.execute(new_stmt)).scalar_one()

    active_stmt = select(func.count()).where(
        Patient.clinic_id == clinic_id, Patient.status == patients_rules.DEFAULT_STATUS
    )
    active_patients = (await db.execute(active_stmt)).scalar_one()

    rows_stmt = (
        select(Patient)
        .where(
            Patient.clinic_id == clinic_id,
            Patient.created_at >= start,
            Patient.created_at < end_exclusive,
        )
        .order_by(Patient.created_at.desc())
    )
    patients = (await db.execute(rows_stmt)).scalars().all()
    rows = [
        PatientReportRow(
            patient_id=p.id,
            expediente_number=p.expediente_number,
            full_name=p.full_name,
            status=p.status,
            created_at=p.created_at,
        )
        for p in patients
    ]
    return PatientsReportOut(
        date_from=date_from,
        date_to=date_to,
        new_patients=new_patients,
        active_patients=active_patients,
        rows=rows,
    )


# ---------------------------------------------------------------------- 2. agenda


async def build_appointments_report(
    db: AsyncSession, *, clinic_id: uuid.UUID, date_from: date, date_to: date
) -> AppointmentsReportOut:
    start, end_exclusive = _date_bounds(date_from, date_to)
    base_filter = (
        Appointment.clinic_id == clinic_id,
        Appointment.starts_at >= start,
        Appointment.starts_at < end_exclusive,
    )

    counts_stmt = (
        select(Appointment.status, func.count()).where(*base_filter).group_by(Appointment.status)
    )
    counts_by_status = {status: count for status, count in (await db.execute(counts_stmt)).all()}

    rows_stmt = (
        select(Appointment, Patient.full_name, IamUser.full_name)
        .join(Patient, Patient.id == Appointment.patient_id)
        .join(Provider, Provider.id == Appointment.provider_id)
        .join(IamUser, IamUser.id == Provider.user_id)
        .where(*base_filter)
        .order_by(Appointment.starts_at.desc())
    )
    rows = [
        AppointmentReportRow(
            appointment_id=appt.id,
            patient_name=patient_name,
            provider_name=provider_name,
            appointment_type=appt.appointment_type,
            starts_at=appt.starts_at,
            status=appt.status,
        )
        for appt, patient_name, provider_name in (await db.execute(rows_stmt)).all()
    ]
    return AppointmentsReportOut(
        date_from=date_from,
        date_to=date_to,
        counts_by_status=counts_by_status,
        no_show_rate=rules.no_show_rate(counts_by_status),
        rows=rows,
    )


# ------------------------------------------------------------------- 3. produccion


async def build_production_report(
    db: AsyncSession, *, clinic_id: uuid.UUID, date_from: date, date_to: date
) -> ProductionReportOut:
    start, end_exclusive = _date_bounds(date_from, date_to)
    stmt = (
        select(ProcedurePerformed, Charge.amount, IamUser.full_name, Patient.full_name)
        .join(Charge, Charge.procedure_performed_id == ProcedurePerformed.id)
        .join(IamUser, IamUser.id == ProcedurePerformed.professional_id)
        .join(Patient, Patient.id == ProcedurePerformed.patient_id)
        .where(
            ProcedurePerformed.clinic_id == clinic_id,
            ProcedurePerformed.performed_at >= start,
            ProcedurePerformed.performed_at < end_exclusive,
            # Un cargo cancelado (regla 2) no cuenta como produccion cobrable.
            Charge.is_active.is_(True),
        )
        .order_by(ProcedurePerformed.performed_at.desc())
    )
    rows = [
        ProductionReportRow(
            procedure_performed_id=performed.id,
            professional_id=performed.professional_id,
            professional_name=professional_name,
            patient_name=patient_name,
            procedure_name=performed.procedure_name,
            performed_at=performed.performed_at,
            amount=amount,
        )
        for performed, amount, professional_name, patient_name in (await db.execute(stmt)).all()
    ]
    totals = rules.sum_amounts_by_key([(row.professional_id, row.amount) for row in rows])
    names = {row.professional_id: row.professional_name for row in rows}
    by_professional = [
        ProfessionalTotal(professional_id=pid, professional_name=names[pid], total_amount=total)
        for pid, total in totals.items()
    ]
    total_amount = sum(totals.values(), Decimal("0.00"))
    return ProductionReportOut(
        date_from=date_from,
        date_to=date_to,
        total_amount=total_amount,
        by_professional=by_professional,
        rows=rows,
    )


# ------------------------------------------------------------------------ 4. planes


async def build_treatment_plans_report(
    db: AsyncSession, *, clinic_id: uuid.UUID, date_from: date, date_to: date
) -> TreatmentPlansReportOut:
    start, end_exclusive = _date_bounds(date_from, date_to)
    base_filter = (
        TreatmentPlan.clinic_id == clinic_id,
        TreatmentPlan.created_at >= start,
        TreatmentPlan.created_at < end_exclusive,
    )

    counts_stmt = (
        select(TreatmentPlan.status, func.count())
        .where(*base_filter)
        .group_by(TreatmentPlan.status)
    )
    counts_by_status = {status: count for status, count in (await db.execute(counts_stmt)).all()}
    pending_count = sum(counts_by_status.get(s, 0) for s in rules.PENDING_PLAN_STATUSES)
    accepted_count = sum(counts_by_status.get(s, 0) for s in rules.ACCEPTED_PLAN_STATUSES)

    rows_stmt = (
        select(TreatmentPlan, Patient.full_name)
        .join(Patient, Patient.id == TreatmentPlan.patient_id)
        .where(*base_filter)
        .order_by(TreatmentPlan.created_at.desc())
    )
    rows = [
        TreatmentPlanReportRow(
            plan_id=plan.id,
            patient_name=patient_name,
            title=plan.title,
            status=plan.status,
            created_at=plan.created_at,
            accepted_at=plan.accepted_at,
        )
        for plan, patient_name in (await db.execute(rows_stmt)).all()
    ]
    return TreatmentPlansReportOut(
        date_from=date_from,
        date_to=date_to,
        counts_by_status=counts_by_status,
        pending_count=pending_count,
        accepted_count=accepted_count,
        rows=rows,
    )


# ---------------------------------------------------------------- 5. cuentas por cobrar


async def build_accounts_receivable_report(
    db: AsyncSession, *, clinic_id: uuid.UUID
) -> AccountsReceivableOut:
    """A diferencia de los demas reportes, este es una fotografia del momento (no
    recibe rango de fechas): un saldo pendiente de hace 3 meses sigue siendo una
    cuenta por cobrar hoy, sin importar cuando se generó el cargo."""
    stmt = (
        select(Charge, Patient.full_name)
        .join(Patient, Patient.id == Charge.patient_id)
        .where(Charge.clinic_id == clinic_id, Charge.is_active.is_(True))
        .order_by(Charge.created_at.asc())
    )
    pairs = (await db.execute(stmt)).all()
    applied_by_charge = await billing_service.applied_amounts_by_charge(
        db, charge_ids=[charge.id for charge, _ in pairs]
    )

    rows: list[AccountsReceivableRow] = []
    total_balance_due = Decimal("0.00")
    for charge, patient_name in pairs:
        applied = applied_by_charge[charge.id]
        balance = billing_rules.charge_balance(charge.amount, applied)
        status = billing_rules.charge_computed_status(
            is_active=charge.is_active, amount=charge.amount, applied=applied
        )
        if status not in ("PENDIENTE", "PARCIAL"):
            continue
        total_balance_due += balance
        rows.append(
            AccountsReceivableRow(
                charge_id=charge.id,
                patient_name=patient_name,
                description=charge.description,
                amount=charge.amount,
                applied_amount=applied,
                balance=balance,
                computed_status=status,
                created_at=charge.created_at,
            )
        )
    return AccountsReceivableOut(as_of=date.today(), total_balance_due=total_balance_due, rows=rows)


# ------------------------------------------------------------------------- 6. IA


async def build_ai_usage_report(
    db: AsyncSession, *, clinic_id: uuid.UUID, date_from: date, date_to: date
) -> AiUsageReportOut:
    start, end_exclusive = _date_bounds(date_from, date_to)
    base_filter = (
        AiSuggestion.clinic_id == clinic_id,
        AiSuggestion.created_at >= start,
        AiSuggestion.created_at < end_exclusive,
    )

    status_stmt = (
        select(AiSuggestion.status, func.count()).where(*base_filter).group_by(AiSuggestion.status)
    )
    counts_by_status = {s: c for s, c in (await db.execute(status_stmt)).all()}

    action_stmt = (
        select(AiSuggestion.action_type, func.count())
        .where(*base_filter)
        .group_by(AiSuggestion.action_type)
    )
    counts_by_action_type = {a: c for a, c in (await db.execute(action_stmt)).all()}

    rows_stmt = select(AiSuggestion).where(*base_filter).order_by(AiSuggestion.created_at.desc())
    rows = [
        AiUsageReportRow(
            suggestion_id=s.id,
            action_type=s.action_type,
            status=s.status,
            model_name=s.model_name,
            created_at=s.created_at,
            reviewed_at=s.reviewed_at,
        )
        for s in (await db.execute(rows_stmt)).scalars().all()
    ]
    return AiUsageReportOut(
        date_from=date_from,
        date_to=date_to,
        counts_by_status=counts_by_status,
        counts_by_action_type=counts_by_action_type,
        rows=rows,
    )


# --------------------------------------------------------------------- exportar CSV


def rows_to_csv(model_cls: type[BaseModel], rows: Sequence[BaseModel]) -> str:
    fieldnames = list(model_cls.model_fields.keys())
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {key: "" if value is None else str(value) for key, value in row.model_dump().items()}
        )
    return buffer.getvalue()


async def log_export(
    db: AsyncSession,
    *,
    clinic_id: uuid.UUID,
    actor_id: uuid.UUID,
    report_name: str,
    date_from: date | None,
    date_to: date | None,
) -> None:
    """Regla de seguridad (CLAUDE.md sec. 5): las exportaciones quedan auditadas."""
    await audit_service.log(
        db,
        action="reports.export",
        actor_user_id=actor_id,
        clinic_id=clinic_id,
        entity_type="report",
        entity_id=report_name,
        details={
            "date_from": date_from.isoformat() if date_from else None,
            "date_to": date_to.isoformat() if date_to else None,
        },
    )
    await db.commit()


# --------------------------------------------------------------- tablero por rol


async def _user_permission_codes(
    db: AsyncSession, *, user_id: uuid.UUID, clinic_id: uuid.UUID
) -> set[str]:
    stmt = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserClinic, UserClinic.role_id == Role.id)
        .where(UserClinic.user_id == user_id, UserClinic.clinic_id == clinic_id)
    )
    return {code for code, in (await db.execute(stmt)).all()}


async def build_dashboard(
    db: AsyncSession, *, clinic_id: uuid.UUID, actor_id: uuid.UUID
) -> DashboardOut:
    """Cada seccion del tablero de inicio se arma solo si el usuario ya tiene el
    permiso de lectura del modulo correspondiente (patients.read, agenda.read, etc.)
    -- a diferencia de la pantalla "Reportes" completa, que exige `reports.read`
    (solo superadmin/admin_clinica/caja segun docs/MATRIZ_PERMISOS.md). Asi cada rol
    ve un tablero relevante en su pagina de inicio sin ampliar el alcance de
    `reports.read`. Ver docs/PENDIENTES_CLINICOS.md."""
    codes = await _user_permission_codes(db, user_id=actor_id, clinic_id=clinic_id)
    today = date.today()
    out = DashboardOut()

    if "patients.read" in codes:
        active_patients = (
            await db.execute(
                select(func.count()).where(
                    Patient.clinic_id == clinic_id, Patient.status == patients_rules.DEFAULT_STATUS
                )
            )
        ).scalar_one()
        start30, _ = _date_bounds(today - timedelta(days=30), today)
        new_last_30_days = (
            await db.execute(
                select(func.count()).where(
                    Patient.clinic_id == clinic_id, Patient.created_at >= start30
                )
            )
        ).scalar_one()
        out.patients = PatientsDashboardSummary(
            active_patients=active_patients, new_last_30_days=new_last_30_days
        )

    if "agenda.read" in codes:
        start_today, end_today = _date_bounds(today, today)
        counts_stmt = (
            select(Appointment.status, func.count())
            .where(
                Appointment.clinic_id == clinic_id,
                Appointment.starts_at >= start_today,
                Appointment.starts_at < end_today,
            )
            .group_by(Appointment.status)
        )
        counts_by_status = {s: c for s, c in (await db.execute(counts_stmt)).all()}
        out.agenda_today = AgendaDashboardSummary(
            total_today=sum(counts_by_status.values()), counts_by_status=counts_by_status
        )

    if "treatment.read" in codes:
        pending_count = (
            await db.execute(
                select(func.count()).where(
                    TreatmentPlan.clinic_id == clinic_id,
                    TreatmentPlan.status.in_(rules.PENDING_PLAN_STATUSES),
                )
            )
        ).scalar_one()
        start30, _ = _date_bounds(today - timedelta(days=30), today)
        accepted_last_30_days = (
            await db.execute(
                select(func.count()).where(
                    TreatmentPlan.clinic_id == clinic_id,
                    TreatmentPlan.status.in_(rules.ACCEPTED_PLAN_STATUSES),
                    TreatmentPlan.accepted_at >= start30,
                )
            )
        ).scalar_one()
        out.treatment = TreatmentDashboardSummary(
            pending_plans=pending_count, accepted_last_30_days=accepted_last_30_days
        )

    billing_enabled = "billing.read" in codes and await billing_service.get_billing_settings(
        db, clinic_id=clinic_id
    )
    if billing_enabled:
        ar = await build_accounts_receivable_report(db, clinic_id=clinic_id)
        current_session = await billing_service.get_current_cash_session(db, clinic_id=clinic_id)
        out.billing = BillingDashboardSummary(
            balance_due_total=ar.total_balance_due, cash_session_open=current_session is not None
        )

    # Fase "Publicacion en Hostinger" sec. 6, cambio #4: con AI_ENABLED=false
    # el widget no se arma (no solo se oculta en el frontend) -- menos una
    # cosa que ocultar del lado del cliente.
    if get_settings().ai_enabled and ("ai.use" in codes or "ai.configure" in codes):
        pending_review = (
            await db.execute(
                select(func.count()).where(
                    AiSuggestion.clinic_id == clinic_id, AiSuggestion.status == "PENDING"
                )
            )
        ).scalar_one()
        start30, _ = _date_bounds(today - timedelta(days=30), today)
        accepted_last_30_days = (
            await db.execute(
                select(func.count()).where(
                    AiSuggestion.clinic_id == clinic_id,
                    AiSuggestion.status == "ACCEPTED",
                    AiSuggestion.reviewed_at >= start30,
                )
            )
        ).scalar_one()
        rejected_last_30_days = (
            await db.execute(
                select(func.count()).where(
                    AiSuggestion.clinic_id == clinic_id,
                    AiSuggestion.status == "REJECTED",
                    AiSuggestion.reviewed_at >= start30,
                )
            )
        ).scalar_one()
        out.ai_usage = AiUsageDashboardSummary(
            pending_review=pending_review,
            accepted_last_30_days=accepted_last_30_days,
            rejected_last_30_days=rejected_last_30_days,
        )

    return out
