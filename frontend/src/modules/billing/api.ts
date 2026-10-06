import { apiRequest, apiRequestBlobUrl } from '../../api/client'
import type {
  BillingSettingsOut,
  CashSessionOut,
  ChargeOut,
  PatientBillingSummaryOut,
  PaymentCreateInput,
  PaymentOut,
} from './types'

export async function listCharges(patientId: string): Promise<ChargeOut[]> {
  return apiRequest<ChargeOut[]>(`/patients/${patientId}/charges`)
}

export async function cancelCharge(chargeId: string, reason: string): Promise<ChargeOut> {
  return apiRequest<ChargeOut>(`/charges/${chargeId}/cancel`, { method: 'POST', body: { reason } })
}

export async function listPayments(patientId: string): Promise<PaymentOut[]> {
  return apiRequest<PaymentOut[]>(`/patients/${patientId}/payments`)
}

export async function createPayment(patientId: string, input: PaymentCreateInput): Promise<PaymentOut> {
  return apiRequest<PaymentOut>(`/patients/${patientId}/payments`, { method: 'POST', body: input })
}

export async function getReceiptBlobUrl(paymentId: string): Promise<string> {
  return apiRequestBlobUrl(`/payments/${paymentId}/receipt`)
}

export async function cancelPayment(paymentId: string, reason: string): Promise<PaymentOut> {
  return apiRequest<PaymentOut>(`/payments/${paymentId}/cancel`, { method: 'POST', body: { reason } })
}

export async function getBillingSummary(patientId: string): Promise<PatientBillingSummaryOut> {
  return apiRequest<PatientBillingSummaryOut>(`/patients/${patientId}/billing-summary`)
}

export async function openCashSession(openingAmount: string): Promise<CashSessionOut> {
  return apiRequest<CashSessionOut>('/cash-sessions/open', {
    method: 'POST',
    body: { opening_amount: openingAmount },
  })
}

export async function getCurrentCashSession(): Promise<CashSessionOut | null> {
  return apiRequest<CashSessionOut | null>('/cash-sessions/current')
}

export async function closeCashSession(
  sessionId: string,
  closingAmount: string,
  notes?: string,
): Promise<CashSessionOut> {
  return apiRequest<CashSessionOut>(`/cash-sessions/${sessionId}/close`, {
    method: 'POST',
    body: { closing_amount: closingAmount, notes: notes || null },
  })
}

export async function getBillingSettings(): Promise<BillingSettingsOut> {
  return apiRequest<BillingSettingsOut>('/billing/settings')
}

export async function updateBillingSettings(billingEnabled: boolean): Promise<BillingSettingsOut> {
  return apiRequest<BillingSettingsOut>('/billing/settings', {
    method: 'PUT',
    body: { billing_enabled: billingEnabled },
  })
}
