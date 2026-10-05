import { useEffect, useState } from 'react'
import { apiRequestBlobUrl } from '../../api/client'
import styles from './PatientHeader.module.css'
import { STATUS_LABELS, type PatientSummaryOut } from './types'

function initials(fullName: string): string {
  return fullName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('')
}

function usePhotoUrl(patientId: string, hasPhoto: boolean): string | null {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!hasPhoto) return

    let objectUrl: string | null = null
    let cancelled = false
    apiRequestBlobUrl(`/patients/${patientId}/photo`).then((u) => {
      if (cancelled) {
        URL.revokeObjectURL(u)
        return
      }
      objectUrl = u
      setUrl(u)
    })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [patientId, hasPhoto])

  return url
}

/** Encabezado persistente del paciente: nombre, edad, foto opcional y barra de alertas. */
export function PatientHeader({ summary }: { summary: PatientSummaryOut }) {
  const photoUrl = usePhotoUrl(summary.id, summary.has_photo)

  return (
    <div className={styles.header}>
      {photoUrl ? (
        <img className={styles.photo} src={photoUrl} alt="" />
      ) : (
        <div className={styles.photo}>{initials(summary.full_name)}</div>
      )}

      <div className={styles.info}>
        <h1 className={styles.name}>{summary.full_name}</h1>
        <p className={styles.meta}>
          {summary.age} anos · Expediente #{summary.expediente_number}{' '}
          <span className={styles.status}>{STATUS_LABELS[summary.status]}</span>
        </p>
      </div>

      <div className={styles.alerts}>
        {summary.alerts.map((alert) => (
          <div key={alert} className={styles.alert}>
            {alert}
          </div>
        ))}
      </div>
    </div>
  )
}
