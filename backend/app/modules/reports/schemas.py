import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

# --------------------------------------------------------------------- 1. pacientes


class PatientReportRow(BaseModel):
    patient_id: uuid.UUID
    expediente_number: str
    full_name: str
    status: str
    created_at: datetime


class PatientsReportOut(BaseModel):
    date_from: date
    date_to: date
    new_patients: int
    active_patients: int
    rows: list[PatientReportRow]


# ---------------------------------------------------------------------- 2. agenda


class AppointmentReportRow(BaseModel):
    appointment_id: uuid.UUID
    patient_name: str
    provider_name: str
    appointment_type: str
    starts_at: datetime
    status: str


class AppointmentsReportOut(BaseModel):
    date_from: date
    date_to: date
    counts_by_status: dict[str, int]
    no_show_rate: Decimal
    rows: list[AppointmentReportRow]


# ------------------------------------------------------------------- 3. produccion


class ProfessionalTotal(BaseModel):
    professional_id: uuid.UUID
    professional_name: str
    total_amount: Decimal


class ProductionReportRow(BaseModel):
    procedure_performed_id: uuid.UUID
    professional_id: uuid.UUID
    professional_name: str
    patient_name: str
    procedure_name: str
    performed_at: datetime
    amount: Decimal


class ProductionReportOut(BaseModel):
    date_from: date
    date_to: date
    total_amount: Decimal
    by_professional: list[ProfessionalTotal]
    rows: list[ProductionReportRow]


# ------------------------------------------------------------------------ 4. planes


class TreatmentPlanReportRow(BaseModel):
    plan_id: uuid.UUID
    patient_name: str
    title: str
    status: str
    created_at: datetime
    accepted_at: datetime | None


class TreatmentPlansReportOut(BaseModel):
    date_from: date
    date_to: date
    counts_by_status: dict[str, int]
    pending_count: int
    accepted_count: int
    rows: list[TreatmentPlanReportRow]


# ---------------------------------------------------------------- 5. cuentas por cobrar


class AccountsReceivableRow(BaseModel):
    charge_id: uuid.UUID
    patient_name: str
    description: str | None
    amount: Decimal
    applied_amount: Decimal
    balance: Decimal
    computed_status: str
    created_at: datetime


class AccountsReceivableOut(BaseModel):
    as_of: date
    total_balance_due: Decimal
    rows: list[AccountsReceivableRow]


# ------------------------------------------------------------------------- 6. IA


class AiUsageReportRow(BaseModel):
    suggestion_id: uuid.UUID
    action_type: str
    status: str
    model_name: str
    created_at: datetime
    reviewed_at: datetime | None


class AiUsageReportOut(BaseModel):
    date_from: date
    date_to: date
    counts_by_status: dict[str, int]
    counts_by_action_type: dict[str, int]
    rows: list[AiUsageReportRow]


# --------------------------------------------------------------- tablero por rol


class PatientsDashboardSummary(BaseModel):
    active_patients: int
    new_last_30_days: int


class AgendaDashboardSummary(BaseModel):
    total_today: int
    counts_by_status: dict[str, int]


class TreatmentDashboardSummary(BaseModel):
    pending_plans: int
    accepted_last_30_days: int


class BillingDashboardSummary(BaseModel):
    balance_due_total: Decimal
    cash_session_open: bool


class AiUsageDashboardSummary(BaseModel):
    pending_review: int
    accepted_last_30_days: int
    rejected_last_30_days: int


class DashboardOut(BaseModel):
    patients: PatientsDashboardSummary | None = None
    agenda_today: AgendaDashboardSummary | None = None
    treatment: TreatmentDashboardSummary | None = None
    billing: BillingDashboardSummary | None = None
    ai_usage: AiUsageDashboardSummary | None = None
