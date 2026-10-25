import { useRef, useState, type ChangeEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { ApiRequestError } from '../../api/client'
import * as agendaApi from '../agenda/api'
import { STATUS_LABELS as APPOINTMENT_STATUS_LABELS } from '../agenda/catalog'
import * as encountersApi from '../encounters/api'
import { NOTE_STATUS_LABELS } from '../encounters/types'
import { canWritePatients, canWriteRecords } from '../auth/roles'
import { useActiveRole, useAuthStore } from '../auth/store'
import * as api from './api'
import styles from './PatientDetailPage.module.css'
import {
  CONTACT_ROLE_LABELS,
  STATUS_LABELS,
  type ContactRole,
  type PatientOut,
  type SexCode,
  type StatusCode,
} from './types'

function EditPatientForm({ patientId, patient }: { patientId: string; patient: PatientOut }) {
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [firstName, setFirstName] = useState(patient.first_name)
  const [lastNamePaternal, setLastNamePaternal] = useState(patient.last_name_paternal)
  const [lastNameMaternal, setLastNameMaternal] = useState(patient.last_name_maternal ?? '')
  const [sex, setSex] = useState<SexCode | ''>(patient.sex ?? '')
  const [phone, setPhone] = useState(patient.phone ?? '')
  const [email, setEmail] = useState(patient.email ?? '')
  const [address, setAddress] = useState(patient.address ?? '')
  const [error, setError] = useState<string | null>(null)

  const updateMutation = useMutation({
    mutationFn: () =>
      api.updatePatient(patientId, {
        first_name: firstName,
        last_name_paternal: lastNamePaternal,
        last_name_maternal: lastNameMaternal || null,
        sex: sex || null,
        phone: phone || null,
        email: email || null,
        address: address || null,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patient', patientId] })
      queryClient.invalidateQueries({ queryKey: ['patient-summary', patientId] })
      setEditing(false)
      setError(null)
    },
    onError: (err: unknown) => {
      setError(err instanceof ApiRequestError ? err.message : 'No se pudieron guardar los datos')
    },
  })

  if (!editing) {
    return (
      <button className={styles.linkButton} type="button" onClick={() => setEditing(true)}>
        Editar datos
      </button>
    )
  }

  return (
    <form
      className={styles.form}
      onSubmit={(e) => {
        e.preventDefault()
        updateMutation.mutate()
      }}
    >
      <h2>Editar datos</h2>
      {error && <div className={styles.errorBox}>{error}</div>}
      <input
        type="text"
        placeholder="Nombre(s)"
        required
        value={firstName}
        onChange={(e) => setFirstName(e.target.value)}
      />
      <input
        type="text"
        placeholder="Apellido paterno"
        required
        value={lastNamePaternal}
        onChange={(e) => setLastNamePaternal(e.target.value)}
      />
      <input
        type="text"
        placeholder="Apellido materno"
        value={lastNameMaternal}
        onChange={(e) => setLastNameMaternal(e.target.value)}
      />
      <select aria-label="Sexo" value={sex} onChange={(e) => setSex(e.target.value as SexCode | '')}>
        <option value="">Sexo sin especificar</option>
        <option value="F">Femenino</option>
        <option value="M">Masculino</option>
        <option value="X">Otro / prefiere no decir</option>
      </select>
      <input
        type="text"
        placeholder="Telefono del paciente"
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
      />
      <input
        type="email"
        placeholder="Correo del paciente"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <input
        type="text"
        placeholder="Direccion"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
      />
      <button className={styles.primaryButton} type="submit" disabled={updateMutation.isPending}>
        {updateMutation.isPending ? 'Guardando...' : 'Guardar datos'}
      </button>
      <button className={styles.linkButton} type="button" onClick={() => setEditing(false)}>
        Cancelar
      </button>
    </form>
  )
}

export function ResumenTab({ patientId }: { patientId: string }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const accessToken = useAuthStore((s) => s.accessToken)
  const activeClinicId = useAuthStore((s) => s.activeClinicId)
  const activeRole = useActiveRole()
  const canWrite = canWritePatients(activeRole)
  const canStartEncounter = canWriteRecords(activeRole)

  const patientQuery = useQuery({
    queryKey: ['patient', patientId],
    queryFn: () => api.getPatient(patientId),
  })
  const contactsQuery = useQuery({
    queryKey: ['patient-contacts', patientId],
    queryFn: () => api.listContacts(patientId),
  })
  const timelineQuery = useQuery({
    queryKey: ['patient-timeline', patientId],
    queryFn: () => encountersApi.getPatientTimeline(patientId),
  })
  // Historial de citas del paciente (asistio/no asistio/etc.): rango amplio fijo
  // (2 anos atras, 1 ano adelante) porque el endpoint exige starts_from/starts_to.
  const appointmentsQuery = useQuery({
    queryKey: ['patient-appointments', patientId],
    queryFn: () => {
      const now = new Date()
      const startsFrom = new Date(now)
      startsFrom.setFullYear(startsFrom.getFullYear() - 2)
      const startsTo = new Date(now)
      startsTo.setFullYear(startsTo.getFullYear() + 1)
      return agendaApi.listAppointments({
        startsFrom: startsFrom.toISOString(),
        startsTo: startsTo.toISOString(),
        patientId,
      })
    },
  })
  // B3 (Parte B, Fase 12.2): para mostrar el nombre (no solo el id) del profesional
  // tratante y el gabinete por defecto, y para ofrecerlos en el formulario de abajo.
  const providersQuery = useQuery({ queryKey: ['providers'], queryFn: agendaApi.listProviders })
  const resourcesQuery = useQuery({
    queryKey: ['resources'],
    queryFn: () => agendaApi.listResources(),
  })

  const [status, setStatus] = useState<StatusCode | ''>('')
  const [statusReason, setStatusReason] = useState('')
  const [statusError, setStatusError] = useState<string | null>(null)

  const statusMutation = useMutation({
    mutationFn: () =>
      api.updatePatient(patientId, { status: status as StatusCode, status_reason: statusReason }),
    onSuccess: () => {
      setStatusReason('')
      setStatus('')
      setStatusError(null)
      queryClient.invalidateQueries({ queryKey: ['patient', patientId] })
      queryClient.invalidateQueries({ queryKey: ['patient-summary', patientId] })
    },
    onError: (err: unknown) => {
      setStatusError(err instanceof ApiRequestError ? err.message : 'No se pudo cambiar el estado')
    },
  })

  // B3 (Parte B, Fase 12.2): igual que el cambio de estado, cambiar el gabinete o
  // el profesional tratante por defecto exige un motivo (edicion controlada) --
  // el backend lo rechaza sin el (care_assignment_reason).
  const [careProviderId, setCareProviderId] = useState('')
  const [careResourceId, setCareResourceId] = useState('')
  const [careReason, setCareReason] = useState('')
  const [careError, setCareError] = useState<string | null>(null)

  const careAssignmentMutation = useMutation({
    mutationFn: () =>
      api.updatePatient(patientId, {
        primary_provider_id: careProviderId || null,
        default_resource_id: careResourceId || null,
        care_assignment_reason: careReason,
      }),
    onSuccess: () => {
      setCareProviderId('')
      setCareResourceId('')
      setCareReason('')
      setCareError(null)
      queryClient.invalidateQueries({ queryKey: ['patient', patientId] })
    },
    onError: (err: unknown) => {
      setCareError(
        err instanceof ApiRequestError ? err.message : 'No se pudo cambiar la asignacion',
      )
    },
  })

  const [contactRole, setContactRole] = useState<ContactRole>('guardian')
  const [contactName, setContactName] = useState('')
  const [contactRelationship, setContactRelationship] = useState('')
  const [contactPhone, setContactPhone] = useState('')

  const addContactMutation = useMutation({
    mutationFn: () =>
      api.createContact(patientId, {
        role: contactRole,
        full_name: contactName,
        relationship_label: contactRelationship || null,
        phone: contactPhone || null,
      }),
    onSuccess: () => {
      setContactName('')
      setContactRelationship('')
      setContactPhone('')
      queryClient.invalidateQueries({ queryKey: ['patient-contacts', patientId] })
    },
  })

  const deleteContactMutation = useMutation({
    mutationFn: (contactId: string) => api.deleteContact(patientId, contactId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['patient-contacts', patientId] }),
  })

  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)

  async function handlePhotoSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || !accessToken || !activeClinicId) return
    setUploading(true)
    try {
      await api.uploadPatientPhoto(patientId, file, accessToken, activeClinicId)
      queryClient.invalidateQueries({ queryKey: ['patient-summary', patientId] })
    } finally {
      setUploading(false)
    }
  }

  const [chiefComplaint, setChiefComplaint] = useState('')

  // A4: antes esto era un try/finally sin catch -- si createEncounter fallaba (403,
  // 500, red), el boton se volvia a habilitar pero nada explicaba por que no paso
  // nada. useMutation, sin su propio onError, cae en la red de seguridad global
  // (app/globalMutationErrorHandling.ts) que muestra el error igual que cualquier
  // otro "Agregar" de la aplicacion.
  const startEncounterMutation = useMutation({
    mutationFn: () =>
      encountersApi.createEncounter({
        patient_id: patientId,
        chief_complaint: chiefComplaint || null,
      }),
    onSuccess: (encounter) => {
      navigate(`/pacientes/${patientId}/atencion/${encounter.id}`)
    },
  })

  return (
    <div className={styles.grid}>
      <div className={styles.card}>
        <h2>Datos generales</h2>
        {patientQuery.data && (
          <dl>
            <div className={styles.infoRow}>
              <dt>Telefono</dt>
              <dd>{patientQuery.data.phone ?? '-'}</dd>
            </div>
            <div className={styles.infoRow}>
              <dt>Correo</dt>
              <dd>{patientQuery.data.email ?? '-'}</dd>
            </div>
            <div className={styles.infoRow}>
              <dt>Direccion</dt>
              <dd>{patientQuery.data.address ?? '-'}</dd>
            </div>
            <div className={styles.infoRow}>
              <dt>Sexo</dt>
              <dd>{patientQuery.data.sex ?? '-'}</dd>
            </div>
            <div className={styles.infoRow}>
              <dt>Profesional tratante</dt>
              <dd>
                {providersQuery.data?.find((p) => p.id === patientQuery.data?.primary_provider_id)
                  ?.full_name ?? 'Sin asignar'}
              </dd>
            </div>
            <div className={styles.infoRow}>
              <dt>Gabinete por defecto</dt>
              <dd>
                {resourcesQuery.data?.find((r) => r.id === patientQuery.data?.default_resource_id)
                  ?.name ?? 'Sin asignar'}
              </dd>
            </div>
          </dl>
        )}

        {canWrite && (
          <>
            <button
              className={styles.primaryButton}
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? 'Subiendo...' : 'Cambiar foto'}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg"
              hidden
              onChange={handlePhotoSelected}
            />

            {patientQuery.data && <EditPatientForm patientId={patientId} patient={patientQuery.data} />}

            <form
              className={styles.form}
              onSubmit={(e) => {
                e.preventDefault()
                statusMutation.mutate()
              }}
            >
              <h2>Cambiar estado</h2>
              {statusError && <div className={styles.errorBox}>{statusError}</div>}
              <select
                aria-label="Cambiar estado"
                value={status}
                onChange={(e) => setStatus(e.target.value as StatusCode | '')}
              >
                <option value="">Selecciona un estado...</option>
                {Object.entries(STATUS_LABELS).map(([code, label]) => (
                  <option key={code} value={code}>
                    {label}
                  </option>
                ))}
              </select>
              <input
                type="text"
                placeholder="Motivo del cambio"
                value={statusReason}
                onChange={(e) => setStatusReason(e.target.value)}
              />
              <button
                className={styles.primaryButton}
                type="submit"
                disabled={!status || !statusReason.trim() || statusMutation.isPending}
              >
                {statusMutation.isPending ? 'Guardando...' : 'Guardar estado'}
              </button>
            </form>

            <form
              className={styles.form}
              onSubmit={(e) => {
                e.preventDefault()
                careAssignmentMutation.mutate()
              }}
            >
              <h2>Profesional y gabinete por defecto</h2>
              {careError && <div className={styles.errorBox}>{careError}</div>}
              <select
                aria-label="Profesional tratante"
                value={careProviderId}
                onChange={(e) => setCareProviderId(e.target.value)}
              >
                <option value="">Sin cambios</option>
                {providersQuery.data?.map((provider) => (
                  <option key={provider.id} value={provider.id}>
                    {provider.full_name}
                  </option>
                ))}
              </select>
              <select
                aria-label="Gabinete por defecto"
                value={careResourceId}
                onChange={(e) => setCareResourceId(e.target.value)}
              >
                <option value="">Sin cambios</option>
                {resourcesQuery.data?.map((resource) => (
                  <option key={resource.id} value={resource.id}>
                    {resource.name}
                  </option>
                ))}
              </select>
              <input
                type="text"
                placeholder="Motivo de la asignacion"
                value={careReason}
                onChange={(e) => setCareReason(e.target.value)}
              />
              <button
                className={styles.primaryButton}
                type="submit"
                disabled={
                  (!careProviderId && !careResourceId) ||
                  !careReason.trim() ||
                  careAssignmentMutation.isPending
                }
              >
                {careAssignmentMutation.isPending ? 'Guardando...' : 'Guardar asignacion'}
              </button>
            </form>
          </>
        )}
      </div>

      <div className={styles.card}>
        <h2>Contactos</h2>
        {contactsQuery.data?.map((contact) => (
          <div key={contact.id} className={styles.contactItem}>
            <span>
              {contact.full_name} — {CONTACT_ROLE_LABELS[contact.role]}
              {contact.phone && ` · ${contact.phone}`}
            </span>
            {canWrite && (
              <button
                className={styles.linkButton}
                type="button"
                onClick={() => deleteContactMutation.mutate(contact.id)}
              >
                Quitar
              </button>
            )}
          </div>
        ))}
        {contactsQuery.data?.length === 0 && <p>Sin contactos registrados.</p>}

        {canWrite && (
          <form
            className={styles.form}
            onSubmit={(e) => {
              e.preventDefault()
              addContactMutation.mutate()
            }}
          >
            <select
              aria-label="Rol del contacto"
              value={contactRole}
              onChange={(e) => setContactRole(e.target.value as ContactRole)}
            >
              {Object.entries(CONTACT_ROLE_LABELS).map(([code, label]) => (
                <option key={code} value={code}>
                  {label}
                </option>
              ))}
            </select>
            <input
              type="text"
              placeholder="Nombre"
              required
              value={contactName}
              onChange={(e) => setContactName(e.target.value)}
            />
            <input
              type="text"
              placeholder="Parentesco"
              value={contactRelationship}
              onChange={(e) => setContactRelationship(e.target.value)}
            />
            <input
              type="text"
              placeholder="Telefono"
              value={contactPhone}
              onChange={(e) => setContactPhone(e.target.value)}
            />
            <button className={styles.primaryButton} type="submit" disabled={addContactMutation.isPending}>
              Agregar contacto
            </button>
          </form>
        )}
      </div>

      <div className={styles.card}>
        <h2>Linea de tiempo clinica</h2>

        {canStartEncounter && (
          <form
            className={styles.form}
            onSubmit={(e) => {
              e.preventDefault()
              startEncounterMutation.mutate()
            }}
          >
            <input
              type="text"
              placeholder="Motivo de la consulta (opcional)"
              value={chiefComplaint}
              onChange={(e) => setChiefComplaint(e.target.value)}
            />
            <button
              className={styles.primaryButton}
              type="submit"
              disabled={startEncounterMutation.isPending}
            >
              {startEncounterMutation.isPending ? 'Iniciando...' : 'Iniciar atencion'}
            </button>
          </form>
        )}

        {timelineQuery.data?.length === 0 && <p>Sin atenciones registradas.</p>}
        {timelineQuery.data?.map((entry) => (
          <div key={entry.encounter_id} className={styles.contactItem}>
            <span>
              {new Date(entry.started_at).toLocaleString('es-MX')} —{' '}
              {entry.chief_complaint ?? 'Sin motivo registrado'} ({entry.professional_name})
              {entry.notes.length > 0 && (
                <> · {entry.notes.map((n) => NOTE_STATUS_LABELS[n.status]).join(', ')}</>
              )}
            </span>
            <button
              className={styles.linkButton}
              type="button"
              onClick={() => navigate(`/pacientes/${patientId}/atencion/${entry.encounter_id}`)}
            >
              Ver
            </button>
          </div>
        ))}
      </div>

      <div className={styles.card}>
        <h2>Citas</h2>
        {appointmentsQuery.data?.length === 0 && <p>Sin citas registradas.</p>}
        {appointmentsQuery.data
          ?.slice()
          .sort((a, b) => b.starts_at.localeCompare(a.starts_at))
          .map((appt) => (
            <div key={appt.id} className={styles.contactItem}>
              <span>
                {new Date(appt.starts_at).toLocaleString('es-MX')} — {appt.appointment_type} ·{' '}
                {APPOINTMENT_STATUS_LABELS[appt.status]}
              </span>
            </div>
          ))}
      </div>
    </div>
  )
}
