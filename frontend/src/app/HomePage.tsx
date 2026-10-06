import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { canReadReports } from '../modules/auth/roles'
import { useActiveRole, useAuthStore } from '../modules/auth/store'
import * as reportsApi from '../modules/reports/api'
import styles from './HomePage.module.css'

function money(value: string): string {
  return `$${Number(value).toLocaleString('es-MX', { minimumFractionDigits: 2 })}`
}

export function HomePage() {
  const user = useAuthStore((s) => s.user)
  const activeRole = useActiveRole()
  const dashboardQuery = useQuery({
    queryKey: ['reports-dashboard'],
    queryFn: reportsApi.getDashboard,
  })
  const dashboard = dashboardQuery.data

  return (
    <section className={styles.page}>
      <div className={styles.header}>
        <h1>Hola, {user?.full_name ?? ''}</h1>
        {canReadReports(activeRole) && (
          <Link className={styles.reportsLink} to="/reportes">
            Ver reportes completos →
          </Link>
        )}
      </div>

      {!dashboard && <p>Cargando tablero...</p>}

      {dashboard && (
        <div className={styles.grid}>
          {dashboard.patients && (
            <div className={styles.card}>
              <h2>Pacientes</h2>
              <div className={styles.cardRow}>
                <span>Activos</span>
                <strong>{dashboard.patients.active_patients}</strong>
              </div>
              <div className={styles.cardRow}>
                <span>Nuevos (ultimos 30 dias)</span>
                <strong>{dashboard.patients.new_last_30_days}</strong>
              </div>
            </div>
          )}

          {dashboard.agenda_today && (
            <div className={styles.card}>
              <h2>Agenda de hoy</h2>
              <div className={styles.cardRow}>
                <span>Citas hoy</span>
                <strong>{dashboard.agenda_today.total_today}</strong>
              </div>
              {Object.entries(dashboard.agenda_today.counts_by_status).map(([status, count]) => (
                <div className={styles.cardRow} key={status}>
                  <span>{status}</span>
                  <strong>{count}</strong>
                </div>
              ))}
              {dashboard.agenda_today.total_today === 0 && <p>Sin citas agendadas para hoy.</p>}
            </div>
          )}

          {dashboard.treatment && (
            <div className={styles.card}>
              <h2>Tratamientos</h2>
              <div className={styles.cardRow}>
                <span>Planes pendientes</span>
                <strong>{dashboard.treatment.pending_plans}</strong>
              </div>
              <div className={styles.cardRow}>
                <span>Aceptados (ultimos 30 dias)</span>
                <strong>{dashboard.treatment.accepted_last_30_days}</strong>
              </div>
            </div>
          )}

          {dashboard.billing && (
            <div className={styles.card}>
              <h2>Cobranza</h2>
              <div className={styles.cardRow}>
                <span>Saldo total por cobrar</span>
                <strong className={styles.danger}>
                  {money(dashboard.billing.balance_due_total)}
                </strong>
              </div>
              <div className={styles.cardRow}>
                <span>Sesion de caja</span>
                <strong>{dashboard.billing.cash_session_open ? 'Abierta' : 'Cerrada'}</strong>
              </div>
            </div>
          )}

          {dashboard.ai_usage && (
            <div className={styles.card}>
              <h2>Asistente de IA</h2>
              <div className={styles.cardRow}>
                <span>Sugerencias por revisar</span>
                <strong>{dashboard.ai_usage.pending_review}</strong>
              </div>
              <div className={styles.cardRow}>
                <span>Aceptadas (ultimos 30 dias)</span>
                <strong>{dashboard.ai_usage.accepted_last_30_days}</strong>
              </div>
              <div className={styles.cardRow}>
                <span>Rechazadas (ultimos 30 dias)</span>
                <strong>{dashboard.ai_usage.rejected_last_30_days}</strong>
              </div>
            </div>
          )}

          {!dashboard.patients &&
            !dashboard.agenda_today &&
            !dashboard.treatment &&
            !dashboard.billing &&
            !dashboard.ai_usage && <p>No hay informacion disponible para tu rol todavia.</p>}
        </div>
      )}
    </section>
  )
}
