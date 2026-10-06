import { Fragment, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as api from './api'
import { PAYMENT_METHOD_LABELS } from './catalog'
import styles from './CashSessionPage.module.css'

function money(value: string): string {
  return `$${Number(value).toLocaleString('es-MX', { minimumFractionDigits: 2 })}`
}

function OpenSessionForm() {
  const queryClient = useQueryClient()
  const [openingAmount, setOpeningAmount] = useState('')

  const openMutation = useMutation({
    mutationFn: () => api.openCashSession(openingAmount),
    onSuccess: () => {
      setOpeningAmount('')
      queryClient.invalidateQueries({ queryKey: ['cash-session-current'] })
    },
  })

  return (
    <form
      className={styles.form}
      onSubmit={(e) => {
        e.preventDefault()
        openMutation.mutate()
      }}
    >
      <h2>Abrir caja</h2>
      <input
        type="number"
        step="0.01"
        min="0"
        placeholder="Monto inicial de efectivo"
        required
        value={openingAmount}
        onChange={(e) => setOpeningAmount(e.target.value)}
      />
      <button className={styles.primaryButton} type="submit" disabled={!openingAmount || openMutation.isPending}>
        Abrir caja
      </button>
    </form>
  )
}

function OpenSessionDetail({ session }: { session: NonNullable<ReturnType<typeof useOpenSession>['data']> }) {
  const queryClient = useQueryClient()
  const [closingAmount, setClosingAmount] = useState('')
  const [notes, setNotes] = useState('')

  const closeMutation = useMutation({
    mutationFn: () => api.closeCashSession(session.id, closingAmount, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cash-session-current'] })
    },
  })

  return (
    <div className={styles.card}>
      <h2>Caja abierta</h2>
      <dl className={styles.statusGrid}>
        <dt>Abierta</dt>
        <dd>{new Date(session.opened_at).toLocaleString('es-MX')}</dd>
        <dt>Monto inicial</dt>
        <dd>{money(session.opening_amount)}</dd>
        {Object.entries(session.totals_by_method).map(([method, total]) => (
          <Fragment key={method}>
            <dt>{PAYMENT_METHOD_LABELS[method as keyof typeof PAYMENT_METHOD_LABELS]}</dt>
            <dd>{money(total)}</dd>
          </Fragment>
        ))}
        <dt>Efectivo esperado</dt>
        <dd>
          <strong>{money(session.expected_cash)}</strong>
        </dd>
      </dl>

      <form
        className={styles.form}
        onSubmit={(e) => {
          e.preventDefault()
          closeMutation.mutate()
        }}
      >
        <h3>Cerrar caja</h3>
        <input
          type="number"
          step="0.01"
          min="0"
          placeholder="Efectivo contado"
          required
          value={closingAmount}
          onChange={(e) => setClosingAmount(e.target.value)}
        />
        <input
          type="text"
          placeholder="Notas (opcional)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
        <button
          className={styles.primaryButton}
          type="submit"
          disabled={!closingAmount || closeMutation.isPending}
        >
          Cerrar caja
        </button>
      </form>
    </div>
  )
}

function useOpenSession() {
  return useQuery({ queryKey: ['cash-session-current'], queryFn: api.getCurrentCashSession })
}

export function CashSessionPage() {
  const sessionQuery = useOpenSession()

  if (sessionQuery.isLoading) return <p>Cargando caja...</p>

  return (
    <section className={styles.page}>
      <h1>Corte de caja</h1>
      {sessionQuery.data ? <OpenSessionDetail session={sessionQuery.data} /> : <OpenSessionForm />}
    </section>
  )
}
