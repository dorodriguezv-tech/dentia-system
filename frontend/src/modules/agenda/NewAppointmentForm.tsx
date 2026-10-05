import { useState } from 'react'
import * as patientsApi from '../patients/api'
import type { PatientListItemOut } from '../patients/types'
import { APPOINTMENT_TYPE_CODES, APPOINTMENT_TYPES } from './catalog'
import { combineDateAndTime } from './dateUtils'
import styles from './NewAppointmentForm.module.css'
import type { AppointmentType, ProviderOut, ResourceOut } from './types'

interface NewAppointmentFormProps {
  date: Date
  hour: number
  minute: number
  providers: ProviderOut[]
  resources: ResourceOut[]
  defaultProviderId: string
  pending: boolean
  onClose: () => void
  onSubmit: (data: {
    patient_id: string
    provider_id: string
    resource_id: string | null
    appointment_type: AppointmentType
    starts_at: string
  }) => void
}

export function NewAppointmentForm({
  date,
  hour,
  minute,
  providers,
  resources,
  defaultProviderId,
  pending,
  onClose,
  onSubmit,
}: NewAppointmentFormProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<PatientListItemOut[]>([])
  const [selectedPatient, setSelectedPatient] = useState<PatientListItemOut | null>(null)
  const [providerId, setProviderId] = useState(defaultProviderId)
  const [resourceId, setResourceId] = useState('')
  const [appointmentType, setAppointmentType] = useState<AppointmentType>('consulta')

  const starts = combineDateAndTime(date, hour, minute)

  async function handleSearch(value: string) {
    setQuery(value)
    setSelectedPatient(null)
    if (value.trim().length < 2) {
      setResults([])
      return
    }
    setResults(await patientsApi.searchPatients(value))
  }

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h3>Nueva cita</h3>
        <button className={styles.closeButton} type="button" onClick={onClose}>
          Cerrar
        </button>
      </div>
      <p className={styles.when}>
        {starts.toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long' })} a las{' '}
        {starts.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })}
      </p>

      {selectedPatient ? (
        <div className={styles.selectedPatient}>
          {selectedPatient.full_name}
          <button className={styles.closeButton} type="button" onClick={() => setSelectedPatient(null)}>
            Cambiar
          </button>
        </div>
      ) : (
        <>
          <input
            type="text"
            placeholder="Buscar paciente por nombre..."
            value={query}
            onChange={(e) => void handleSearch(e.target.value)}
          />
          {results.length > 0 && (
            <ul className={styles.results}>
              {results.map((patient) => (
                <li key={patient.id}>
                  <button type="button" onClick={() => setSelectedPatient(patient)}>
                    {patient.full_name} — exp. {patient.expediente_number}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      <select value={providerId} onChange={(e) => setProviderId(e.target.value)}>
        {providers.map((provider) => (
          <option key={provider.id} value={provider.id}>
            {provider.full_name}
          </option>
        ))}
      </select>

      <select value={resourceId} onChange={(e) => setResourceId(e.target.value)}>
        <option value="">Sin gabinete asignado</option>
        {resources.map((resource) => (
          <option key={resource.id} value={resource.id}>
            {resource.name}
          </option>
        ))}
      </select>

      <select
        value={appointmentType}
        onChange={(e) => setAppointmentType(e.target.value as AppointmentType)}
      >
        {APPOINTMENT_TYPE_CODES.map((code) => (
          <option key={code} value={code}>
            {APPOINTMENT_TYPES[code].label} ({APPOINTMENT_TYPES[code].defaultMinutes} min)
          </option>
        ))}
      </select>

      <button
        className={styles.submitButton}
        type="button"
        disabled={!selectedPatient || !providerId || pending}
        onClick={() =>
          selectedPatient &&
          onSubmit({
            patient_id: selectedPatient.id,
            provider_id: providerId,
            resource_id: resourceId || null,
            appointment_type: appointmentType,
            starts_at: starts.toISOString(),
          })
        }
      >
        {pending ? 'Agendando...' : 'Agendar cita'}
      </button>
    </div>
  )
}
