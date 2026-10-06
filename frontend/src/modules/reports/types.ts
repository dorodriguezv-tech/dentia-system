export interface PatientReportRow {
  patient_id: string
  expediente_number: string
  full_name: string
  status: string
  created_at: string
}

export interface PatientsReportOut {
  date_from: string
  date_to: string
  new_patients: number
  active_patients: number
  rows: PatientReportRow[]
}

export interface AppointmentReportRow {
  appointment_id: string
  patient_name: string
  provider_name: string
  appointment_type: string
  starts_at: string
  status: string
}

export interface AppointmentsReportOut {
  date_from: string
  date_to: string
  counts_by_status: Record<string, number>
  no_show_rate: string
  rows: AppointmentReportRow[]
}

export interface ProfessionalTotal {
  professional_id: string
  professional_name: string
  total_amount: string
}

export interface ProductionReportRow {
  procedure_performed_id: string
  professional_id: string
  professional_name: string
  patient_name: string
  procedure_name: string
  performed_at: string
  amount: string
}

export interface ProductionReportOut {
  date_from: string
  date_to: string
  total_amount: string
  by_professional: ProfessionalTotal[]
  rows: ProductionReportRow[]
}

export interface TreatmentPlanReportRow {
  plan_id: string
  patient_name: string
  title: string
  status: string
  created_at: string
  accepted_at: string | null
}

export interface TreatmentPlansReportOut {
  date_from: string
  date_to: string
  counts_by_status: Record<string, number>
  pending_count: number
  accepted_count: number
  rows: TreatmentPlanReportRow[]
}

export interface AccountsReceivableRow {
  charge_id: string
  patient_name: string
  description: string | null
  amount: string
  applied_amount: string
  balance: string
  computed_status: string
  created_at: string
}

export interface AccountsReceivableOut {
  as_of: string
  total_balance_due: string
  rows: AccountsReceivableRow[]
}

export interface AiUsageReportRow {
  suggestion_id: string
  action_type: string
  status: string
  model_name: string
  created_at: string
  reviewed_at: string | null
}

export interface AiUsageReportOut {
  date_from: string
  date_to: string
  counts_by_status: Record<string, number>
  counts_by_action_type: Record<string, number>
  rows: AiUsageReportRow[]
}

export interface PatientsDashboardSummary {
  active_patients: number
  new_last_30_days: number
}

export interface AgendaDashboardSummary {
  total_today: number
  counts_by_status: Record<string, number>
}

export interface TreatmentDashboardSummary {
  pending_plans: number
  accepted_last_30_days: number
}

export interface BillingDashboardSummary {
  balance_due_total: string
  cash_session_open: boolean
}

export interface AiUsageDashboardSummary {
  pending_review: number
  accepted_last_30_days: number
  rejected_last_30_days: number
}

export interface DashboardOut {
  patients: PatientsDashboardSummary | null
  agenda_today: AgendaDashboardSummary | null
  treatment: TreatmentDashboardSummary | null
  billing: BillingDashboardSummary | null
  ai_usage: AiUsageDashboardSummary | null
}

export interface DateRange {
  date_from: string
  date_to: string
}
