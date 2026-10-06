import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as api from './api'
import { CHARGE_STATUS_LABELS, PAYMENT_METHOD_LABELS, PAYMENT_METHODS } from './catalog'
import styles from './AccountTab.module.css'
import type { ChargeOut, PaymentMethod, PaymentOut } from './types'

function money(value: string): string {
  return `$${Number(value).toLocaleString('es-MX', { minimumFractionDigits: 2 })}`
}

function SummaryCard({ patientId }: { patientId: string }) {
  const summaryQuery = useQuery({
    queryKey: ['billing-summary', patientId],
    queryFn: () => api.getBillingSummary(patientId),
  })
  if (!summaryQuery.data) return null
  const s = summaryQuery.data
  return (
    <div className={styles.summaryGrid}>
      <div className={styles.summaryItem}>
        <span>Total cargado</span>
        <strong>{money(s.total_charged)}</strong>
      </div>
      <div className={styles.summaryItem}>
        <span>Total pagado</span>
        <strong>{money(s.total_paid)}</strong>
      </div>
      <div className={styles.summaryItem}>
        <span>Credito disponible</span>
        <strong>{money(s.total_credit)}</strong>
      </div>
      <div className={`${styles.summaryItem} ${styles.balanceDue}`}>
        <span>Saldo pendiente</span>
        <strong>{money(s.balance_due)}</strong>
      </div>
    </div>
  )
}

function ChargeRow({ charge, canWrite, onCancelled }: { charge: ChargeOut; canWrite: boolean; onCancelled: () => void }) {
  const [reason, setReason] = useState('')
  const [cancelling, setCancelling] = useState(false)
  const cancelMutation = useMutation({
    mutationFn: () => api.cancelCharge(charge.id, reason),
    onSuccess: () => {
      setCancelling(false)
      onCancelled()
    },
  })

  return (
    <div className={styles.row}>
      <span>
        {charge.description ?? 'Procedimiento'} — {money(charge.amount)}
        {' · '}
        <span className={styles[`status_${charge.computed_status}`]}>
          {CHARGE_STATUS_LABELS[charge.computed_status]}
        </span>
        {charge.computed_status !== 'PAGADO' && charge.computed_status !== 'CANCELADO' && (
          <> · Saldo: {money(charge.balance)}</>
        )}
      </span>
      {canWrite && charge.is_active && charge.computed_status === 'PENDIENTE' && !cancelling && (
        <button className={styles.linkButton} type="button" onClick={() => setCancelling(true)}>
          Cancelar
        </button>
      )}
      {cancelling && (
        <span className={styles.rowActions}>
          <input
            type="text"
            placeholder="Motivo de cancelacion"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
          <button
            className={styles.linkButton}
            type="button"
            disabled={!reason.trim()}
            onClick={() => cancelMutation.mutate()}
          >
            Confirmar
          </button>
        </span>
      )}
      {cancelMutation.isError && <p className={styles.errorBox}>No se pudo cancelar (¿tiene pagos aplicados?).</p>}
    </div>
  )
}

function PaymentRow({ payment, canWrite, onCancelled }: { payment: PaymentOut; canWrite: boolean; onCancelled: () => void }) {
  const [reason, setReason] = useState('')
  const [cancelling, setCancelling] = useState(false)
  const cancelMutation = useMutation({
    mutationFn: () => api.cancelPayment(payment.id, reason),
    onSuccess: () => {
      setCancelling(false)
      onCancelled()
    },
  })

  async function openReceipt() {
    const newTab = window.open('', '_blank')
    const url = await api.getReceiptBlobUrl(payment.id)
    if (newTab) newTab.location.href = url
  }

  return (
    <div className={styles.row}>
      <span>
        {PAYMENT_METHOD_LABELS[payment.method]} — {money(payment.amount)}
        {' · '}
        {new Date(payment.received_at).toLocaleString('es-MX')}
        {!payment.is_active && ` — Cancelado: ${payment.cancel_reason}`}
        {payment.is_active && Number(payment.unallocated_amount) > 0 && (
          <> · Anticipo sin aplicar: {money(payment.unallocated_amount)}</>
        )}
      </span>
      <span className={styles.rowActions}>
        <button className={styles.linkButton} type="button" onClick={openReceipt}>
          Recibo
        </button>
        {canWrite && payment.is_active && !cancelling && (
          <button className={styles.linkButton} type="button" onClick={() => setCancelling(true)}>
            Cancelar
          </button>
        )}
        {cancelling && (
          <>
            <input
              type="text"
              placeholder="Motivo de cancelacion"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <button
              className={styles.linkButton}
              type="button"
              disabled={!reason.trim()}
              onClick={() => cancelMutation.mutate()}
            >
              Confirmar
            </button>
          </>
        )}
      </span>
    </div>
  )
}

function NewPaymentForm({ patientId, charges }: { patientId: string; charges: ChargeOut[] }) {
  const queryClient = useQueryClient()
  const [method, setMethod] = useState<PaymentMethod>('efectivo')
  const [amount, setAmount] = useState('')
  const [reference, setReference] = useState('')
  const [notes, setNotes] = useState('')
  const [allocationAmounts, setAllocationAmounts] = useState<Record<string, string>>({})

  const pendingCharges = charges.filter(
    (c) => c.is_active && (c.computed_status === 'PENDIENTE' || c.computed_status === 'PARCIAL'),
  )

  const createMutation = useMutation({
    mutationFn: () =>
      api.createPayment(patientId, {
        method,
        amount,
        reference: reference || null,
        notes: notes || null,
        allocations: Object.entries(allocationAmounts)
          .filter(([, value]) => value && Number(value) > 0)
          .map(([charge_id, value]) => ({ charge_id, amount: value })),
      }),
    onSuccess: () => {
      setAmount('')
      setReference('')
      setNotes('')
      setAllocationAmounts({})
      queryClient.invalidateQueries({ queryKey: ['charges', patientId] })
      queryClient.invalidateQueries({ queryKey: ['payments', patientId] })
      queryClient.invalidateQueries({ queryKey: ['billing-summary', patientId] })
    },
  })

  return (
    <form
      className={styles.form}
      onSubmit={(e) => {
        e.preventDefault()
        createMutation.mutate()
      }}
    >
      <select value={method} onChange={(e) => setMethod(e.target.value as PaymentMethod)}>
        {PAYMENT_METHODS.map((m) => (
          <option key={m} value={m}>
            {PAYMENT_METHOD_LABELS[m]}
          </option>
        ))}
      </select>
      <input
        type="number"
        step="0.01"
        min="0.01"
        placeholder="Monto recibido"
        required
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
      />
      {method !== 'efectivo' && (
        <input
          type="text"
          placeholder="Referencia / autorizacion"
          value={reference}
          onChange={(e) => setReference(e.target.value)}
        />
      )}
      <input type="text" placeholder="Notas (opcional)" value={notes} onChange={(e) => setNotes(e.target.value)} />

      {pendingCharges.length > 0 && (
        <fieldset className={styles.allocations}>
          <legend>Aplicar a cargos pendientes (opcional; lo que no se aplique queda como anticipo)</legend>
          {pendingCharges.map((charge) => (
            <label key={charge.id} className={styles.allocationRow}>
              <span>
                {charge.description ?? 'Procedimiento'} (saldo {money(charge.balance)})
              </span>
              <input
                type="number"
                step="0.01"
                min="0"
                placeholder="0.00"
                value={allocationAmounts[charge.id] ?? ''}
                onChange={(e) =>
                  setAllocationAmounts((prev) => ({ ...prev, [charge.id]: e.target.value }))
                }
              />
            </label>
          ))}
        </fieldset>
      )}

      <button className={styles.primaryButton} type="submit" disabled={!amount || createMutation.isPending}>
        Registrar pago
      </button>
      {createMutation.isError && <p className={styles.errorBox}>No se pudo registrar el pago.</p>}
    </form>
  )
}

export function AccountTab({ patientId, canWrite }: { patientId: string; canWrite: boolean }) {
  const queryClient = useQueryClient()
  const settingsQuery = useQuery({ queryKey: ['billing-settings'], queryFn: api.getBillingSettings })
  const chargesQuery = useQuery({ queryKey: ['charges', patientId], queryFn: () => api.listCharges(patientId) })
  const paymentsQuery = useQuery({ queryKey: ['payments', patientId], queryFn: () => api.listPayments(patientId) })

  function invalidateAll() {
    queryClient.invalidateQueries({ queryKey: ['charges', patientId] })
    queryClient.invalidateQueries({ queryKey: ['payments', patientId] })
    queryClient.invalidateQueries({ queryKey: ['billing-summary', patientId] })
  }

  if (settingsQuery.data && !settingsQuery.data.billing_enabled) {
    return (
      <div className={styles.page}>
        <p className={styles.disabledBox}>
          La cobranza esta desactivada para esta sucursal (Configuración → Cobranza).
        </p>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <SummaryCard patientId={patientId} />

      <details className={styles.card} open>
        <summary>Cargos</summary>
        {chargesQuery.data?.map((charge) => (
          <ChargeRow key={charge.id} charge={charge} canWrite={canWrite} onCancelled={invalidateAll} />
        ))}
        {!chargesQuery.data?.length && <p>Sin cargos registrados.</p>}
      </details>

      <details className={styles.card} open>
        <summary>Pagos</summary>
        {paymentsQuery.data?.map((payment) => (
          <PaymentRow key={payment.id} payment={payment} canWrite={canWrite} onCancelled={invalidateAll} />
        ))}
        {!paymentsQuery.data?.length && <p>Sin pagos registrados.</p>}
        {canWrite && <NewPaymentForm patientId={patientId} charges={chargesQuery.data ?? []} />}
      </details>
    </div>
  )
}
