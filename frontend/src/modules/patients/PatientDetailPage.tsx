import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import * as api from './api'
import { ExpedienteTab } from './ExpedienteTab'
import styles from './PatientDetailPage.module.css'
import { PatientHeader } from './PatientHeader'
import { ResumenTab } from './ResumenTab'

type Tab = 'resumen' | 'expediente'

export function PatientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const patientId = id as string
  const [tab, setTab] = useState<Tab>('resumen')

  const summaryQuery = useQuery({
    queryKey: ['patient-summary', patientId],
    queryFn: () => api.getPatientSummary(patientId),
  })

  if (summaryQuery.isLoading) return <p>Cargando paciente...</p>
  if (summaryQuery.isError || !summaryQuery.data) return <p>No se pudo cargar el paciente.</p>

  return (
    <section>
      <PatientHeader summary={summaryQuery.data} />

      <div className={styles.tabs}>
        <button
          className={tab === 'resumen' ? styles.tabActive : styles.tab}
          type="button"
          onClick={() => setTab('resumen')}
        >
          Resumen
        </button>
        <button
          className={tab === 'expediente' ? styles.tabActive : styles.tab}
          type="button"
          onClick={() => setTab('expediente')}
        >
          Expediente
        </button>
      </div>

      {tab === 'resumen' ? (
        <ResumenTab patientId={patientId} />
      ) : (
        <ExpedienteTab patientId={patientId} />
      )}
    </section>
  )
}
