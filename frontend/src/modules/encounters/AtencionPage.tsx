import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import * as recordsApi from '../records/api'
import * as api from './api'
import styles from './AtencionPage.module.css'
import { NOTE_STATUS_LABELS, type ClinicalNoteFields, type ClinicalNoteOut } from './types'

const AUTOSAVE_INTERVAL_MS = 10_000

function ReasonForm({
  label,
  onSubmit,
  pending,
}: {
  label: string
  onSubmit: (reason: string) => void
  pending: boolean
}) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')

  if (!open) {
    return (
      <button className={styles.secondaryButton} type="button" onClick={() => setOpen(true)}>
        {label}
      </button>
    )
  }

  return (
    <form
      className={styles.inlineForm}
      onSubmit={(e) => {
        e.preventDefault()
        onSubmit(reason)
      }}
    >
      <input
        type="text"
        placeholder="Motivo"
        required
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <button className={styles.secondaryButton} type="submit" disabled={!reason.trim() || pending}>
        Confirmar {label.toLowerCase()}
      </button>
      <button className={styles.linkButton} type="button" onClick={() => setOpen(false)}>
        Cancelar
      </button>
    </form>
  )
}

function noteFieldsOf(note: ClinicalNoteOut): ClinicalNoteFields {
  return {
    soap_s: note.soap_s ?? '',
    soap_o: note.soap_o ?? '',
    soap_a: note.soap_a ?? '',
    soap_p: note.soap_p ?? '',
    free_text: note.free_text ?? '',
  }
}

function NoteEditor({
  note,
  patientId,
  encounterId,
}: {
  note: ClinicalNoteOut
  patientId: string
  encounterId: string
}) {
  const queryClient = useQueryClient()
  const [fields, setFields] = useState<ClinicalNoteFields>(() => noteFieldsOf(note))
  const fieldsRef = useRef(fields)
  const dirtyRef = useRef(false)

  const saveMutation = useMutation({
    mutationFn: (data: ClinicalNoteFields) => api.updateNote(note.id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['encounter-notes', encounterId] }),
  })

  useEffect(() => {
    if (note.status !== 'DRAFT') return
    const interval = setInterval(() => {
      if (dirtyRef.current) {
        dirtyRef.current = false
        saveMutation.mutate(fieldsRef.current)
      }
    }, AUTOSAVE_INTERVAL_MS)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [note.id, note.status])

  function updateField(field: keyof ClinicalNoteFields, value: string) {
    const next = { ...fieldsRef.current, [field]: value }
    fieldsRef.current = next
    dirtyRef.current = true
    setFields(next)
  }

  const [alertsToConfirm, setAlertsToConfirm] = useState<string[] | null>(null)

  const finalizeMutation = useMutation({
    mutationFn: (alertsAcknowledged: boolean) => api.finalizeNote(note.id, alertsAcknowledged),
    onSuccess: () => {
      setAlertsToConfirm(null)
      queryClient.invalidateQueries({ queryKey: ['encounter-notes', encounterId] })
      queryClient.invalidateQueries({ queryKey: ['patient-timeline', patientId] })
    },
  })

  async function handleFinalizeClick() {
    if (dirtyRef.current) {
      dirtyRef.current = false
      await saveMutation.mutateAsync(fieldsRef.current)
    }
    const alerts = await recordsApi.getPatientAlerts(patientId)
    if (alerts.length > 0) {
      setAlertsToConfirm(alerts)
    } else {
      finalizeMutation.mutate(false)
    }
  }

  const correctMutation = useMutation({
    mutationFn: (reason: string) => api.correctNote(note.id, reason),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['encounter-notes', encounterId] }),
  })

  const cancelMutation = useMutation({
    mutationFn: (reason: string) => api.cancelNote(note.id, reason),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['encounter-notes', encounterId] }),
  })

  const isEditable = note.status === 'DRAFT'

  return (
    <>
      <p>
        Nota version {note.version} — {NOTE_STATUS_LABELS[note.status]}
        {saveMutation.isPending && ' · Guardando...'}
      </p>
      {note.correction_reason && <p>Motivo de la correccion: {note.correction_reason}</p>}

      <div className={styles.soapGrid}>
        {(
          [
            ['soap_s', 'Subjetivo'],
            ['soap_o', 'Objetivo'],
            ['soap_a', 'Analisis'],
            ['soap_p', 'Plan'],
          ] as const
        ).map(([field, label]) => (
          <label key={field} className={styles.soapField}>
            <span>{label}</span>
            <textarea
              value={fields[field] ?? ''}
              disabled={!isEditable}
              onChange={(e) => updateField(field, e.target.value)}
            />
          </label>
        ))}
        <label className={styles.soapField}>
          <span>Notas adicionales</span>
          <textarea
            value={fields.free_text ?? ''}
            disabled={!isEditable}
            onChange={(e) => updateField('free_text', e.target.value)}
          />
        </label>
      </div>

      {isEditable && (
        <div className={styles.actions}>
          <button className={styles.primaryButton} type="button" onClick={handleFinalizeClick}>
            Finalizar nota
          </button>
          <ReasonForm
            label="Cancelar"
            onSubmit={(reason) => cancelMutation.mutate(reason)}
            pending={cancelMutation.isPending}
          />
        </div>
      )}

      {note.status === 'FINAL' && (
        <div className={styles.actions}>
          <ReasonForm
            label="Corregir"
            onSubmit={(reason) => correctMutation.mutate(reason)}
            pending={correctMutation.isPending}
          />
          <ReasonForm
            label="Cancelar"
            onSubmit={(reason) => cancelMutation.mutate(reason)}
            pending={cancelMutation.isPending}
          />
        </div>
      )}

      {alertsToConfirm && (
        <div className={styles.modalOverlay}>
          <div className={styles.modal}>
            <h2>Alertas criticas del paciente</h2>
            <ul>
              {alertsToConfirm.map((alert) => (
                <li key={alert}>{alert}</li>
              ))}
            </ul>
            <p>Confirma que revisaste estas alertas antes de finalizar la nota.</p>
            <div className={styles.actions}>
              <button
                className={styles.primaryButton}
                type="button"
                disabled={finalizeMutation.isPending}
                onClick={() => finalizeMutation.mutate(true)}
              >
                Confirmar y finalizar
              </button>
              <button className={styles.linkButton} type="button" onClick={() => setAlertsToConfirm(null)}>
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export function AtencionPage() {
  const { patientId, encounterId } = useParams<{ patientId: string; encounterId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const encounterQuery = useQuery({
    queryKey: ['encounter', encounterId],
    queryFn: () => api.getEncounter(encounterId as string),
  })
  const notesQuery = useQuery({
    queryKey: ['encounter-notes', encounterId],
    queryFn: () => api.listEncounterNotes(encounterId as string),
  })

  const notes = notesQuery.data ?? []
  const activeNote = notes.length > 0 ? notes[notes.length - 1] : null
  const priorNotes = notes.slice(0, -1).reverse()

  const createNoteMutation = useMutation({
    mutationFn: () => api.createNote(encounterId as string, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['encounter-notes', encounterId] }),
  })

  useEffect(() => {
    if (notesQuery.isSuccess && notes.length === 0 && !createNoteMutation.isPending) {
      createNoteMutation.mutate()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notesQuery.isSuccess, notes.length])

  if (encounterQuery.isLoading || notesQuery.isLoading || !activeNote) {
    return <p>Cargando atencion...</p>
  }

  return (
    <section className={styles.page}>
      <button className={styles.linkButton} type="button" onClick={() => navigate(`/pacientes/${patientId}`)}>
        Volver al paciente
      </button>

      <h1>Atencion — {encounterQuery.data?.chief_complaint ?? 'Sin motivo registrado'}</h1>

      <NoteEditor key={activeNote.id} note={activeNote} patientId={patientId as string} encounterId={encounterId as string} />

      {priorNotes.length > 0 && (
        <div className={styles.history}>
          <h2>Versiones anteriores</h2>
          {priorNotes.map((note: ClinicalNoteOut) => (
            <details key={note.id} className={styles.historyItem}>
              <summary>
                Version {note.version} — {NOTE_STATUS_LABELS[note.status]}
                {note.correction_reason && ` (motivo: ${note.correction_reason})`}
              </summary>
              <p>
                <strong>S:</strong> {note.soap_s ?? '-'}
              </p>
              <p>
                <strong>O:</strong> {note.soap_o ?? '-'}
              </p>
              <p>
                <strong>A:</strong> {note.soap_a ?? '-'}
              </p>
              <p>
                <strong>P:</strong> {note.soap_p ?? '-'}
              </p>
            </details>
          ))}
        </div>
      )}
    </section>
  )
}
