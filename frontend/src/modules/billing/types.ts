export type PaymentMethod = 'efectivo' | 'tarjeta' | 'transferencia'
export type ChargeStatus = 'PENDIENTE' | 'PARCIAL' | 'PAGADO' | 'CANCELADO'
export type CashSessionStatus = 'ABIERTA' | 'CERRADA'

export interface ChargeOut {
  id: string
  patient_id: string
  procedure_performed_id: string
  amount: string
  description: string | null
  is_active: boolean
  cancel_reason: string | null
  computed_status: ChargeStatus
  applied_amount: string
  balance: string
}

export interface AllocationInput {
  charge_id: string
  amount: string
}

export interface PaymentCreateInput {
  method: PaymentMethod
  amount: string
  reference?: string | null
  notes?: string | null
  allocations: AllocationInput[]
}

export interface AllocationOut {
  id: string
  charge_id: string
  amount_applied: string
}

export interface PaymentOut {
  id: string
  patient_id: string
  method: PaymentMethod
  amount: string
  received_at: string
  reference: string | null
  notes: string | null
  is_active: boolean
  cancel_reason: string | null
  allocated_amount: string
  unallocated_amount: string
  allocations: AllocationOut[]
}

export interface PatientBillingSummaryOut {
  total_charged: string
  total_paid: string
  total_credit: string
  balance_due: string
}

export interface CashSessionOut {
  id: string
  opened_at: string
  opening_amount: string
  status: CashSessionStatus
  closed_at: string | null
  closing_amount: string | null
  notes: string | null
  totals_by_method: Record<PaymentMethod, string>
  expected_cash: string
  cash_difference: string | null
}

export interface BillingSettingsOut {
  billing_enabled: boolean
}
