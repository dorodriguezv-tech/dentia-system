import type { ChargeStatus, PaymentMethod } from './types'

/**
 * Copia minima, solo para la interfaz, del catalogo de
 * backend/app/modules/billing/rules.py (fuente de verdad real).
 */
export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  efectivo: 'Efectivo',
  tarjeta: 'Tarjeta',
  transferencia: 'Transferencia',
}

export const PAYMENT_METHODS = Object.keys(PAYMENT_METHOD_LABELS) as PaymentMethod[]

export const CHARGE_STATUS_LABELS: Record<ChargeStatus, string> = {
  PENDIENTE: 'Pendiente',
  PARCIAL: 'Parcial',
  PAGADO: 'Pagado',
  CANCELADO: 'Cancelado',
}
