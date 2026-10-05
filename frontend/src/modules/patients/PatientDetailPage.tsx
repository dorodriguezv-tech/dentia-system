import { useRef, useState, type ChangeEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { ApiRequestError } from '../../api/client'
import { canWritePatients } from '../auth/roles'
import { useActiveRole, useAuthStore } from '../auth/store'
import * as api from './api'
import styles from './PatientDetailPage.module.css'
import { PatientHeader } from './PatientHeader'
import { CONTACT_ROLE_LABELS, STATUS_LABELS, type ContactRole, type StatusCode } from './types'

export function PatientDetailPage() {
  const { id } = useParams<{ id: string }>()
  const patientId = id as string
  const queryClient = useQueryClient()
  const accessToken = useAuthStore((s) => s.accessToken)
  const activeClinicId = useAuthStore((s) => s.activeClinicId)
  const canWrite = canWritePatients(useActiveRole())

  const summaryQuery = useQuery({
    queryKey: ['patient-summary', patientId],
    queryFn: () => api.getPatientSummary(patientId),
  })
  const patientQuery = useQuery({
    queryKey: ['patient', patientId],
    queryFn: () => api.getPatient(patientId),
  })
  const contactsQuery = useQuery({
    queryKey: ['patient-contacts', patientId],
    queryFn: () => api.listContacts(patientId),
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

  if (summaryQuery.isLoading) return <p>Cargando paciente...</p>
  if (summaryQuery.isError || !summaryQuery.data) return <p>No se pudo cargar el paciente.</p>

  return (
    <section>
      <PatientHeader summary={summaryQuery.data} />

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
              <button
                className={styles.primaryButton}
                type="submit"
                disabled={addContactMutation.isPending}
              >
                Agregar contacto
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  )
}
