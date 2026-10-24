import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useLocation, useParams } from 'react-router-dom'
import {
  canReadBilling,
  canReadDocuments,
  canReadImaging,
  canSignDocuments,
  canWriteBilling,
  canWriteDocuments,
  canWriteImaging,
} from '../auth/roles'
import { useActiveRole } from '../auth/store'
import { AccountTab } from '../billing/AccountTab'
import { ConsentsTab } from '../documents/ConsentsTab'
import { ImagesTab } from '../imaging/ImagesTab'
import { OdontogramaTab } from '../odontogram/OdontogramaTab'
import { TreatmentTab } from '../treatment/TreatmentTab'
import { useReportScreenContext } from '../voice/useReportScreenContext'
import * as api from './api'
import { ExpedienteTab } from './ExpedienteTab'
import styles from './PatientDetailPage.module.css'
import { PatientHeader } from './PatientHeader'
import { ResumenTab } from './ResumenTab'

type Tab =
  | 'resumen'
  | 'expediente'
  | 'odontograma'
  | 'tratamientos'
  | 'consentimientos'
  | 'imagenes'
  | 'cuenta'

function isTab(value: unknown): value is Tab {
  return (
    typeof value === 'string' &&
    ['resumen', 'expediente', 'odontograma', 'tratamientos', 'consentimientos', 'imagenes', 'cuenta'].includes(
      value,
    )
  )
}

export function PatientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const patientId = id as string
  const location = useLocation()
  // Fase 13 ("Dentia"), 13.2: si se navego aqui por una orden de voz
  // ("abre el odontograma de..."), el backend manda la pestaña destino por
  // location.state en vez de la URL (ver useVoiceSession.ts::handleUiAction).
  const requestedTab = (location.state as { tab?: unknown } | null)?.tab
  const [tab, setTab] = useState<Tab>(isTab(requestedTab) ? requestedTab : 'resumen')
  const activeRole = useActiveRole()

  useReportScreenContext({ patientId, tab })

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
        {canReadBilling(activeRole) && (
          <button
            className={tab === 'cuenta' ? styles.tabActive : styles.tab}
            type="button"
            onClick={() => setTab('cuenta')}
          >
            Cuenta
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
          patientName={summaryQuery.data.full_name}
          patientAge={summaryQuery.data.age}
          canWrite={canWriteDocuments(activeRole)}
          canSign={canSignDocuments(activeRole)}
        />
      )}
      {tab === 'imagenes' && <ImagesTab patientId={patientId} canWrite={canWriteImaging(activeRole)} />}
      {tab === 'cuenta' && <AccountTab patientId={patientId} canWrite={canWriteBilling(activeRole)} />}
    </section>
  )
}
