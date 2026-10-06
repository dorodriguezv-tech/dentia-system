import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import * as api from './api'
import styles from './ReportsPage.module.css'
import type { DateRange } from './types'

function money(value: string): string {
  return `$${Number(value).toLocaleString('es-MX', { minimumFractionDigits: 2 })}`
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString('es-MX')
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('es-MX')
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function daysAgoIso(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString().slice(0, 10)
}

type ReportTabKey = 'pacientes' | 'citas' | 'produccion' | 'planes' | 'cuentas' | 'ia'

const TABS: { key: ReportTabKey; label: string }[] = [
  { key: 'pacientes', label: 'Pacientes' },
  { key: 'citas', label: 'Citas' },
  { key: 'produccion', label: 'Produccion' },
  { key: 'planes', label: 'Planes de tratamiento' },
  { key: 'cuentas', label: 'Cuentas por cobrar' },
  { key: 'ia', label: 'Uso del asistente IA' },
]

function CountsByStatus({ counts }: { counts: Record<string, number> }) {
  const entries = Object.entries(counts)
  if (!entries.length) return <p>Sin datos en el periodo.</p>
  return (
    <ul className={styles.countsList}>
      {entries.map(([status, count]) => (
        <li key={status}>
          <span>{status}</span>
          <strong>{count}</strong>
        </li>
      ))}
    </ul>
  )
}

function PatientsReportTab({ range }: { range: DateRange }) {
  const query = useQuery({
    queryKey: ['reports-patients', range],
    queryFn: () => api.getPatientsReport(range),
  })
  if (!query.data) return <p>Cargando...</p>
  const r = query.data
  return (
    <div className={styles.tabContent}>
      <div className={styles.summaryGrid}>
        <div className={styles.summaryItem}>
          <span>Pacientes nuevos en el periodo</span>
          <strong>{r.new_patients}</strong>
        </div>
        <div className={styles.summaryItem}>
          <span>Pacientes activos (total actual)</span>
          <strong>{r.active_patients}</strong>
        </div>
      </div>
      <button
        className={styles.exportButton}
        type="button"
        onClick={() => api.exportPatientsReport(range)}
      >
        Exportar CSV
      </button>
      {r.rows.length > 0 ? (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Expediente</th>
              <th>Nombre</th>
              <th>Estado</th>
              <th>Alta</th>
            </tr>
          </thead>
          <tbody>
            {r.rows.map((row) => (
              <tr key={row.patient_id}>
                <td>{row.expediente_number}</td>
                <td>{row.full_name}</td>
                <td>{row.status}</td>
                <td>{formatDate(row.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>Sin pacientes nuevos en el periodo.</p>
      )}
    </div>
  )
}

function AppointmentsReportTab({ range }: { range: DateRange }) {
  const query = useQuery({
    queryKey: ['reports-appointments', range],
    queryFn: () => api.getAppointmentsReport(range),
  })
  if (!query.data) return <p>Cargando...</p>
  const r = query.data
  return (
    <div className={styles.tabContent}>
      <div className={styles.summaryGrid}>
        <div className={`${styles.summaryItem} ${styles.balanceDue}`}>
          <span>Tasa de no-show</span>
          <strong>{r.no_show_rate}%</strong>
        </div>
      </div>
      <CountsByStatus counts={r.counts_by_status} />
      <button
        className={styles.exportButton}
        type="button"
        onClick={() => api.exportAppointmentsReport(range)}
      >
        Exportar CSV
      </button>
      {r.rows.length > 0 ? (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Paciente</th>
              <th>Profesional</th>
              <th>Tipo</th>
              <th>Inicio</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {r.rows.map((row) => (
              <tr key={row.appointment_id}>
                <td>{row.patient_name}</td>
                <td>{row.provider_name}</td>
                <td>{row.appointment_type}</td>
                <td>{formatDateTime(row.starts_at)}</td>
                <td>{row.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>Sin citas en el periodo.</p>
      )}
    </div>
  )
}

function ProductionReportTab({ range }: { range: DateRange }) {
  const query = useQuery({
    queryKey: ['reports-production', range],
    queryFn: () => api.getProductionReport(range),
  })
  if (!query.data) return <p>Cargando...</p>
  const r = query.data
  return (
    <div className={styles.tabContent}>
      <div className={styles.summaryGrid}>
        <div className={styles.summaryItem}>
          <span>Produccion total</span>
          <strong>{money(r.total_amount)}</strong>
        </div>
      </div>
      {r.by_professional.length > 0 && (
        <ul className={styles.countsList}>
          {r.by_professional.map((p) => (
            <li key={p.professional_id}>
              <span>{p.professional_name}</span>
              <strong>{money(p.total_amount)}</strong>
            </li>
          ))}
        </ul>
      )}
      <button
        className={styles.exportButton}
        type="button"
        onClick={() => api.exportProductionReport(range)}
      >
        Exportar CSV
      </button>
      {r.rows.length > 0 ? (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Profesional</th>
              <th>Paciente</th>
              <th>Procedimiento</th>
              <th>Monto</th>
            </tr>
          </thead>
          <tbody>
            {r.rows.map((row) => (
              <tr key={row.procedure_performed_id}>
                <td>{formatDateTime(row.performed_at)}</td>
                <td>{row.professional_name}</td>
                <td>{row.patient_name}</td>
                <td>{row.procedure_name}</td>
                <td>{money(row.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>Sin produccion en el periodo.</p>
      )}
    </div>
  )
}

function TreatmentPlansReportTab({ range }: { range: DateRange }) {
  const query = useQuery({
    queryKey: ['reports-treatment-plans', range],
    queryFn: () => api.getTreatmentPlansReport(range),
  })
  if (!query.data) return <p>Cargando...</p>
  const r = query.data
  return (
    <div className={styles.tabContent}>
      <div className={styles.summaryGrid}>
        <div className={styles.summaryItem}>
          <span>Pendientes (borrador/presentado)</span>
          <strong>{r.pending_count}</strong>
        </div>
        <div className={styles.summaryItem}>
          <span>Aceptados</span>
          <strong>{r.accepted_count}</strong>
        </div>
      </div>
      <CountsByStatus counts={r.counts_by_status} />
      <button
        className={styles.exportButton}
        type="button"
        onClick={() => api.exportTreatmentPlansReport(range)}
      >
        Exportar CSV
      </button>
      {r.rows.length > 0 ? (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Paciente</th>
              <th>Plan</th>
              <th>Estado</th>
              <th>Creado</th>
              <th>Aceptado</th>
            </tr>
          </thead>
          <tbody>
            {r.rows.map((row) => (
              <tr key={row.plan_id}>
                <td>{row.patient_name}</td>
                <td>{row.title}</td>
                <td>{row.status}</td>
                <td>{formatDate(row.created_at)}</td>
                <td>{row.accepted_at ? formatDate(row.accepted_at) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>Sin planes creados en el periodo.</p>
      )}
    </div>
  )
}

function AccountsReceivableReportTab() {
  const query = useQuery({
    queryKey: ['reports-accounts-receivable'],
    queryFn: () => api.getAccountsReceivableReport(),
  })
  if (!query.data) return <p>Cargando...</p>
  const r = query.data
  return (
    <div className={styles.tabContent}>
      <p className={styles.note}>
        Fotografia al {formatDate(r.as_of)} — no depende del rango de fechas de arriba, un saldo
        pendiente sigue siendo una cuenta por cobrar sin importar cuando se generó el cargo.
      </p>
      <div className={styles.summaryGrid}>
        <div className={`${styles.summaryItem} ${styles.balanceDue}`}>
          <span>Saldo total por cobrar</span>
          <strong>{money(r.total_balance_due)}</strong>
        </div>
      </div>
      <button
        className={styles.exportButton}
        type="button"
        onClick={() => api.exportAccountsReceivableReport()}
      >
        Exportar CSV
      </button>
      {r.rows.length > 0 ? (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Paciente</th>
              <th>Cargo</th>
              <th>Monto</th>
              <th>Aplicado</th>
              <th>Saldo</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {r.rows.map((row) => (
              <tr key={row.charge_id}>
                <td>{row.patient_name}</td>
                <td>{row.description ?? 'Procedimiento'}</td>
                <td>{money(row.amount)}</td>
                <td>{money(row.applied_amount)}</td>
                <td>{money(row.balance)}</td>
                <td>{row.computed_status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>Sin saldos pendientes.</p>
      )}
    </div>
  )
}

function AiUsageReportTab({ range }: { range: DateRange }) {
  const query = useQuery({
    queryKey: ['reports-ai-usage', range],
    queryFn: () => api.getAiUsageReport(range),
  })
  if (!query.data) return <p>Cargando...</p>
  const r = query.data
  return (
    <div className={styles.tabContent}>
      <h3 className={styles.subheading}>Por estado</h3>
      <CountsByStatus counts={r.counts_by_status} />
      <h3 className={styles.subheading}>Por tipo de accion</h3>
      <CountsByStatus counts={r.counts_by_action_type} />
      <button
        className={styles.exportButton}
        type="button"
        onClick={() => api.exportAiUsageReport(range)}
      >
        Exportar CSV
      </button>
      {r.rows.length > 0 ? (
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Tipo de accion</th>
              <th>Estado</th>
              <th>Modelo</th>
              <th>Revisado</th>
            </tr>
          </thead>
          <tbody>
            {r.rows.map((row) => (
              <tr key={row.suggestion_id}>
                <td>{formatDateTime(row.created_at)}</td>
                <td>{row.action_type}</td>
                <td>{row.status}</td>
                <td>{row.model_name}</td>
                <td>{row.reviewed_at ? formatDateTime(row.reviewed_at) : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>Sin sugerencias de IA en el periodo.</p>
      )}
    </div>
  )
}

export function ReportsPage() {
  const [tab, setTab] = useState<ReportTabKey>('pacientes')
  const [dateFrom, setDateFrom] = useState(daysAgoIso(30))
  const [dateTo, setDateTo] = useState(todayIso())
  const range: DateRange = { date_from: dateFrom, date_to: dateTo }

  return (
    <section className={styles.page}>
      <h1>Reportes</h1>

      {tab !== 'cuentas' && (
        <div className={styles.rangePicker}>
          <label>
            Desde
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </label>
          <label>
            Hasta
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </label>
        </div>
      )}

      <div className={styles.tabs}>
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            className={tab === t.key ? styles.tabActive : styles.tab}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'pacientes' && <PatientsReportTab range={range} />}
      {tab === 'citas' && <AppointmentsReportTab range={range} />}
      {tab === 'produccion' && <ProductionReportTab range={range} />}
      {tab === 'planes' && <TreatmentPlansReportTab range={range} />}
      {tab === 'cuentas' && <AccountsReceivableReportTab />}
      {tab === 'ia' && <AiUsageReportTab range={range} />}
    </section>
  )
}
