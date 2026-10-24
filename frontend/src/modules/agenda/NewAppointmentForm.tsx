import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import * as catalogsApi from '../catalogs/api'
import * as patientsApi from '../patients/api'
import type { PatientListItemOut } from '../patients/types'
import { combineDateAndTime } from './dateUtils'
import styles from './NewAppointmentForm.module.css'
import type { AppointmentType, ProviderOut, ResourceOut } from './types'

const SEARCH_DEBOUNCE_MS = 250
const MIN_QUERY_LENGTH = 2

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
  // B2 (Parte B, Fase 12.2): preselecciona el gabinete por defecto del profesional
  // que ya viene elegido (el de la columna/fila en la que se hizo clic).
  const [resourceId, setResourceId] = useState(
    () => providers.find((p) => p.id === defaultProviderId)?.default_resource_id ?? '',
  )
  const [appointmentType, setAppointmentType] = useState<AppointmentType>('')

  // B1 (Parte B, Fase 12.2): catalogo administrable, ya no un literal fijo -- un
  // tipo de cita nuevo que el administrador acaba de crear aparece aqui de
  // inmediato (criterio de aceptacion de B1).
  const appointmentTypesQuery = useQuery({
    queryKey: ['catalog-items', 'appointment_type'],
    queryFn: () => catalogsApi.listCatalogItems('appointment_type', false),
  })
  const appointmentTypes = appointmentTypesQuery.data ?? []
  const effectiveAppointmentType = appointmentType || appointmentTypes[0]?.code || ''

  const starts = combineDateAndTime(date, hour, minute)

  // Antes disparaba una busqueda por cada tecla, sin cancelar la anterior --
  // con conexiones lentas las respuestas podian llegar desordenadas y la UI se
  // sentia trabada. Mismo patron que GlobalSearch (debounce + abort).
  useEffect(() => {
    const trimmed = query.trim()
    // No hace falta limpiar `results` aqui: `visibleResults` (abajo) ya lo
    // ignora mientras el texto sea mas corto que el minimo (mismo patron que
    // GlobalSearch) -- evita un setState sincrono dentro del efecto.
    if (trimmed.length < MIN_QUERY_LENGTH) return
    const controller = new AbortController()
    const timeout = setTimeout(() => {
      patientsApi
        .searchPatients(trimmed, controller.signal)
        .then(setResults)
        .catch(() => undefined)
    }, SEARCH_DEBOUNCE_MS)
    return () => {
      clearTimeout(timeout)
      controller.abort()
    }
  }, [query])

  function handleQueryChange(value: string) {
    setQuery(value)
    setSelectedPatient(null)
  }

  const trimmedQuery = query.trim()
  const visibleResults = trimmedQuery.length >= MIN_QUERY_LENGTH ? results : []

  function defaultResourceForProvider(id: string): string | null {
    return providers.find((p) => p.id === id)?.default_resource_id ?? null
  }

  // B2/B3 (Parte B, Fase 12.2): al elegir un paciente, preselecciona su
  // profesional/gabinete tratante; si el paciente no tiene uno propio, cae al
  // gabinete por defecto del profesional ya elegido.
  function handleSelectPatient(patient: PatientListItemOut) {
    setSelectedPatient(patient)
    const nextProviderId = patient.primary_provider_id || providerId
    setProviderId(nextProviderId)
    const nextResourceId =
      patient.default_resource_id || defaultResourceForProvider(nextProviderId)
    if (nextResourceId) setResourceId(nextResourceId)
  }

  function handleProviderChange(nextProviderId: string) {
    setProviderId(nextProviderId)
    if (!resourceId) {
      const defaultResource = defaultResourceForProvider(nextProviderId)
      if (defaultResource) setResourceId(defaultResource)
    }
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
        {starts.toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long' })} a
        las {starts.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })}
      </p>

      {selectedPatient ? (
        <div className={styles.selectedPatient}>
          {selectedPatient.full_name}
          <button
            className={styles.closeButton}
            type="button"
            onClick={() => setSelectedPatient(null)}
          >
            Cambiar
          </button>
        </div>
      ) : (
        <>
          <input
            type="text"
            aria-label="Buscar paciente por nombre"
            placeholder="Buscar paciente por nombre..."
            value={query}
            onChange={(e) => handleQueryChange(e.target.value)}
          />
          {visibleResults.length > 0 && (
            <ul className={styles.results}>
              {visibleResults.map((patient) => (
                <li key={patient.id}>
                  <button type="button" onClick={() => handleSelectPatient(patient)}>
                    {patient.full_name} — exp. {patient.expediente_number}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      <select
        aria-label="Profesional"
        value={providerId}
        onChange={(e) => handleProviderChange(e.target.value)}
      >
        {providers.map((provider) => (
          <option key={provider.id} value={provider.id}>
            {provider.full_name}
          </option>
        ))}
      </select>

      <select
        aria-label="Gabinete"
        value={resourceId}
        onChange={(e) => setResourceId(e.target.value)}
      >
        <option value="">Sin gabinete asignado</option>
        {resources.map((resource) => (
          <option key={resource.id} value={resource.id}>
            {resource.name}
          </option>
        ))}
      </select>

      <select
        aria-label="Tipo de cita"
        value={effectiveAppointmentType}
        onChange={(e) => setAppointmentType(e.target.value)}
      >
        {appointmentTypes.map((item) => (
          <option key={item.code} value={item.code}>
            {item.name}
            {typeof item.extra.default_minutes === 'number'
              ? ` (${item.extra.default_minutes} min)`
              : ''}
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
            appointment_type: effectiveAppointmentType,
            starts_at: starts.toISOString(),
          })
        }
      >
        {pending ? 'Agendando...' : 'Agendar cita'}
      </button>
    </div>
  )
}
