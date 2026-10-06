import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

from app.core.db import get_db
from app.core.deps import get_clinic_id, get_current_user, require_permission
from app.core.errors import AppError
from app.modules.iam.models import User
from app.modules.reports import service
from app.modules.reports.schemas import (
    AccountsReceivableOut,
    AccountsReceivableRow,
    AiUsageReportOut,
    AiUsageReportRow,
    AppointmentReportRow,
    AppointmentsReportOut,
    DashboardOut,
    PatientReportRow,
    PatientsReportOut,
    ProductionReportOut,
    ProductionReportRow,
    TreatmentPlanReportRow,
    TreatmentPlansReportOut,
)

router = APIRouter(tags=["reports"])


def _resolve_range(date_from: date | None, date_to: date | None) -> tuple[date, date]:
    resolved_from, resolved_to = service.resolve_date_range(date_from, date_to)
    if resolved_from > resolved_to:
        raise AppError(
            "INVALID_DATE_RANGE",
            "La fecha inicial no puede ser posterior a la final",
            status_code=400,
        )
    return resolved_from, resolved_to


def _csv_response(content: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/patients", response_model=PatientsReportOut)
async def get_patients_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("reports.read")),
    db: AsyncSession = Depends(get_db),
) -> PatientsReportOut:
    resolved_from, resolved_to = _resolve_range(date_from, date_to)
    return await service.build_patients_report(
        db, clinic_id=clinic_id, date_from=resolved_from, date_to=resolved_to
    )


@router.get("/reports/patients/export")
async def export_patients_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("reports.read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    resolved_from, resolved_to = _resolve_range(date_from, date_to)
    report = await service.build_patients_report(
        db, clinic_id=clinic_id, date_from=resolved_from, date_to=resolved_to
    )
    csv_content = service.rows_to_csv(PatientReportRow, report.rows)
    await service.log_export(
        db,
        clinic_id=clinic_id,
        actor_id=actor.id,
        report_name="patients",
        date_from=resolved_from,
        date_to=resolved_to,
    )
    return _csv_response(csv_content, "pacientes.csv")


@router.get("/reports/appointments", response_model=AppointmentsReportOut)
async def get_appointments_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("reports.read")),
    db: AsyncSession = Depends(get_db),
) -> AppointmentsReportOut:
    resolved_from, resolved_to = _resolve_range(date_from, date_to)
    return await service.build_appointments_report(
        db, clinic_id=clinic_id, date_from=resolved_from, date_to=resolved_to
    )


@router.get("/reports/appointments/export")
async def export_appointments_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("reports.read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    resolved_from, resolved_to = _resolve_range(date_from, date_to)
    report = await service.build_appointments_report(
        db, clinic_id=clinic_id, date_from=resolved_from, date_to=resolved_to
    )
    csv_content = service.rows_to_csv(AppointmentReportRow, report.rows)
    await service.log_export(
        db,
        clinic_id=clinic_id,
        actor_id=actor.id,
        report_name="appointments",
        date_from=resolved_from,
        date_to=resolved_to,
    )
    return _csv_response(csv_content, "citas.csv")


@router.get("/reports/production", response_model=ProductionReportOut)
async def get_production_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("reports.read")),
    db: AsyncSession = Depends(get_db),
) -> ProductionReportOut:
    resolved_from, resolved_to = _resolve_range(date_from, date_to)
    return await service.build_production_report(
        db, clinic_id=clinic_id, date_from=resolved_from, date_to=resolved_to
    )


@router.get("/reports/production/export")
async def export_production_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("reports.read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    resolved_from, resolved_to = _resolve_range(date_from, date_to)
    report = await service.build_production_report(
        db, clinic_id=clinic_id, date_from=resolved_from, date_to=resolved_to
    )
    csv_content = service.rows_to_csv(ProductionReportRow, report.rows)
    await service.log_export(
        db,
        clinic_id=clinic_id,
        actor_id=actor.id,
        report_name="production",
        date_from=resolved_from,
        date_to=resolved_to,
    )
    return _csv_response(csv_content, "produccion.csv")


@router.get("/reports/treatment-plans", response_model=TreatmentPlansReportOut)
async def get_treatment_plans_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("reports.read")),
    db: AsyncSession = Depends(get_db),
) -> TreatmentPlansReportOut:
    resolved_from, resolved_to = _resolve_range(date_from, date_to)
    return await service.build_treatment_plans_report(
        db, clinic_id=clinic_id, date_from=resolved_from, date_to=resolved_to
    )


@router.get("/reports/treatment-plans/export")
async def export_treatment_plans_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("reports.read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    resolved_from, resolved_to = _resolve_range(date_from, date_to)
    report = await service.build_treatment_plans_report(
        db, clinic_id=clinic_id, date_from=resolved_from, date_to=resolved_to
    )
    csv_content = service.rows_to_csv(TreatmentPlanReportRow, report.rows)
    await service.log_export(
        db,
        clinic_id=clinic_id,
        actor_id=actor.id,
        report_name="treatment-plans",
        date_from=resolved_from,
        date_to=resolved_to,
    )
    return _csv_response(csv_content, "planes-de-tratamiento.csv")


@router.get("/reports/accounts-receivable", response_model=AccountsReceivableOut)
async def get_accounts_receivable_report(
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("reports.read")),
    db: AsyncSession = Depends(get_db),
) -> AccountsReceivableOut:
    return await service.build_accounts_receivable_report(db, clinic_id=clinic_id)


@router.get("/reports/accounts-receivable/export")
async def export_accounts_receivable_report(
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("reports.read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    report = await service.build_accounts_receivable_report(db, clinic_id=clinic_id)
    csv_content = service.rows_to_csv(AccountsReceivableRow, report.rows)
    await service.log_export(
        db,
        clinic_id=clinic_id,
        actor_id=actor.id,
        report_name="accounts-receivable",
        date_from=None,
        date_to=None,
    )
    return _csv_response(csv_content, "cuentas-por-cobrar.csv")


@router.get("/reports/ai-usage", response_model=AiUsageReportOut)
async def get_ai_usage_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    _actor: User = Depends(require_permission("reports.read")),
    db: AsyncSession = Depends(get_db),
) -> AiUsageReportOut:
    resolved_from, resolved_to = _resolve_range(date_from, date_to)
    return await service.build_ai_usage_report(
        db, clinic_id=clinic_id, date_from=resolved_from, date_to=resolved_to
    )


@router.get("/reports/ai-usage/export")
async def export_ai_usage_report(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(require_permission("reports.read")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    resolved_from, resolved_to = _resolve_range(date_from, date_to)
    report = await service.build_ai_usage_report(
        db, clinic_id=clinic_id, date_from=resolved_from, date_to=resolved_to
    )
    csv_content = service.rows_to_csv(AiUsageReportRow, report.rows)
    await service.log_export(
        db,
        clinic_id=clinic_id,
        actor_id=actor.id,
        report_name="ai-usage",
        date_from=resolved_from,
        date_to=resolved_to,
    )
    return _csv_response(csv_content, "uso-asistente-ia.csv")


@router.get("/reports/dashboard", response_model=DashboardOut)
async def get_dashboard(
    clinic_id: uuid.UUID = Depends(get_clinic_id),
    actor: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardOut:
    return await service.build_dashboard(db, clinic_id=clinic_id, actor_id=actor.id)
