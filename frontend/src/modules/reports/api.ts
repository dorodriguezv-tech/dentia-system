import { apiRequest, apiRequestBlobUrl } from '../../api/client'
import type {
  AccountsReceivableOut,
  AiUsageReportOut,
  AppointmentsReportOut,
  DashboardOut,
  DateRange,
  PatientsReportOut,
  ProductionReportOut,
  TreatmentPlansReportOut,
} from './types'

function rangeQuery(range: DateRange): string {
  return new URLSearchParams({ date_from: range.date_from, date_to: range.date_to }).toString()
}

export function getPatientsReport(range: DateRange): Promise<PatientsReportOut> {
  return apiRequest<PatientsReportOut>(`/reports/patients?${rangeQuery(range)}`)
}

export function getAppointmentsReport(range: DateRange): Promise<AppointmentsReportOut> {
  return apiRequest<AppointmentsReportOut>(`/reports/appointments?${rangeQuery(range)}`)
}

export function getProductionReport(range: DateRange): Promise<ProductionReportOut> {
  return apiRequest<ProductionReportOut>(`/reports/production?${rangeQuery(range)}`)
}

export function getTreatmentPlansReport(range: DateRange): Promise<TreatmentPlansReportOut> {
  return apiRequest<TreatmentPlansReportOut>(`/reports/treatment-plans?${rangeQuery(range)}`)
}

export function getAccountsReceivableReport(): Promise<AccountsReceivableOut> {
  return apiRequest<AccountsReceivableOut>('/reports/accounts-receivable')
}

export function getAiUsageReport(range: DateRange): Promise<AiUsageReportOut> {
  return apiRequest<AiUsageReportOut>(`/reports/ai-usage?${rangeQuery(range)}`)
}

export function getDashboard(): Promise<DashboardOut> {
  return apiRequest<DashboardOut>('/reports/dashboard')
}

/**
 * A diferencia del recibo en PDF (que se abre en una pestaña nueva), un CSV se
 * descarga directo: se crea un <a download> temporal a partir del blob y se simula
 * el clic, sin necesidad del patron de ventana sincrona (no hay bloqueo de popups
 * porque nunca se abre una ventana nueva).
 */
async function downloadCsv(path: string, filename: string): Promise<void> {
  const blobUrl = await apiRequestBlobUrl(path)
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(blobUrl)
}

export function exportPatientsReport(range: DateRange): Promise<void> {
  return downloadCsv(`/reports/patients/export?${rangeQuery(range)}`, 'pacientes.csv')
}

export function exportAppointmentsReport(range: DateRange): Promise<void> {
  return downloadCsv(`/reports/appointments/export?${rangeQuery(range)}`, 'citas.csv')
}

export function exportProductionReport(range: DateRange): Promise<void> {
  return downloadCsv(`/reports/production/export?${rangeQuery(range)}`, 'produccion.csv')
}

export function exportTreatmentPlansReport(range: DateRange): Promise<void> {
  return downloadCsv(
    `/reports/treatment-plans/export?${rangeQuery(range)}`,
    'planes-de-tratamiento.csv',
  )
}

export function exportAccountsReceivableReport(): Promise<void> {
  return downloadCsv('/reports/accounts-receivable/export', 'cuentas-por-cobrar.csv')
}

export function exportAiUsageReport(range: DateRange): Promise<void> {
  return downloadCsv(`/reports/ai-usage/export?${rangeQuery(range)}`, 'uso-asistente-ia.csv')
}
