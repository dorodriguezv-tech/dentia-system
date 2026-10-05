import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { OdontogramaTab } from '../odontogram/OdontogramaTab'
import { TreatmentTab } from '../treatment/TreatmentTab'
import * as api from './api'
import { ExpedienteTab } from './ExpedienteTab'
import styles from './PatientDetailPage.module.css'
import { PatientHeader } from './PatientHeader'
import { ResumenTab } from './ResumenTab'

type Tab = 'resumen' | 'expediente' | 'odontograma' | 'tratamientos'

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
        <button
          className={tab === 'odontograma' ? styles.tabActive : styles.tab}
          type="button"
          onClick={() => setTab('odontograma')}
        >
          Odontograma
        </button>
        <button
          className={tab === 'tratamientos' ? styles.tabActive : styles.tab}
          type="button"
          onClick={() => setTab('tratamientos')}
        >
          Tratamientos
        </button>
      </div>

      {tab === 'resumen' && <ResumenTab patientId={patientId} />}
      {tab === 'expediente' && <ExpedienteTab patientId={patientId} />}
      {tab === 'odontograma' && <OdontogramaTab patientId={patientId} />}
      {tab === 'tratamientos' && <TreatmentTab patientId={patientId} />}
    </section>
  )
}
