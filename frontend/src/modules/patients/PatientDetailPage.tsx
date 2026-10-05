import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { canReadDocuments, canReadImaging, canSignDocuments, canWriteDocuments, canWriteImaging } from '../auth/roles'
import { useActiveRole } from '../auth/store'
import { ConsentsTab } from '../documents/ConsentsTab'
import { ImagesTab } from '../imaging/ImagesTab'
import { OdontogramaTab } from '../odontogram/OdontogramaTab'
import { TreatmentTab } from '../treatment/TreatmentTab'
import * as api from './api'
import { ExpedienteTab } from './ExpedienteTab'
import styles from './PatientDetailPage.module.css'
import { PatientHeader } from './PatientHeader'
import { ResumenTab } from './ResumenTab'

type Tab = 'resumen' | 'expediente' | 'odontograma' | 'tratamientos' | 'consentimientos' | 'imagenes'

export function PatientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const patientId = id as string
  const [tab, setTab] = useState<Tab>('resumen')
  const activeRole = useActiveRole()

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
        {canReadDocuments(activeRole) && (
          <button
            className={tab === 'consentimientos' ? styles.tabActive : styles.tab}
            type="button"
            onClick={() => setTab('consentimientos')}
          >
            Consentimientos
          </button>
        )}
        {canReadImaging(activeRole) && (
          <button
            className={tab === 'imagenes' ? styles.tabActive : styles.tab}
            type="button"
            onClick={() => setTab('imagenes')}
          >
            Imágenes
          </button>
        )}
      </div>

      {tab === 'resumen' && <ResumenTab patientId={patientId} />}
      {tab === 'expediente' && <ExpedienteTab patientId={patientId} />}
      {tab === 'odontograma' && <OdontogramaTab patientId={patientId} />}
      {tab === 'tratamientos' && <TreatmentTab patientId={patientId} />}
      {tab === 'consentimientos' && (
        <ConsentsTab
          patientId={patientId}
          canWrite={canWriteDocuments(activeRole)}
          canSign={canSignDocuments(activeRole)}
        />
      )}
      {tab === 'imagenes' && <ImagesTab patientId={patientId} canWrite={canWriteImaging(activeRole)} />}
    </section>
  )
}
