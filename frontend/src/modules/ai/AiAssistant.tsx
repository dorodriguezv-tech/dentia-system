import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiRequestError } from '../../api/client'
import * as recordsApi from '../records/api'
import * as api from './api'
import {
  ACTION_TYPE_DESTINATION,
  ACTION_TYPE_LABELS,
  describeSuggestion,
  needsAlertReview,
  type Destination,
} from './catalog'
import styles from './AiAssistant.module.css'
import type { AiSuggestionOut } from './types'

type MicState = 'inactive' | 'listening' | 'processing'

function EditableFields({
  payload,
  onCancel,
  onSave,
}: {
  payload: Record<string, unknown>
  onCancel: () => void
  onSave: (edits: Record<string, unknown>) => void
}) {
  const editableKeys = Object.keys(payload).filter(
    (key) => typeof payload[key] === 'string' || typeof payload[key] === 'number',
  )
  const [values, setValues] = useState<Record<string, string>>(() =>
    Object.fromEntries(editableKeys.map((key) => [key, String(payload[key] ?? '')])),
  )

  function buildEdits(): Record<string, unknown> {
    const edits: Record<string, unknown> = {}
    for (const key of editableKeys) {
      const original = payload[key]
      edits[key] = typeof original === 'number' ? Number(values[key]) : values[key]
    }
    return edits
  }

  return (
    <div className={styles.editForm}>
      {editableKeys.map((key) => (
        <label key={key} className={styles.editField}>
          <span>{key}</span>
          <input
            type="text"
            value={values[key]}
            onChange={(e) => setValues((v) => ({ ...v, [key]: e.target.value }))}
          />
        </label>
      ))}
      <div className={styles.cardActions}>
        <button className={styles.primaryButton} type="button" onClick={() => onSave(buildEdits())}>
          Guardar y aceptar
        </button>
        <button className={styles.linkButton} type="button" onClick={onCancel}>
          Cancelar
        </button>
      </div>
    </div>
  )
}

function SuggestionCard({
  suggestion,
  alerts,
  onAccept,
  onReject,
}: {
  suggestion: AiSuggestionOut
  alerts: string[]
  onAccept: (id: string, edits?: Record<string, unknown>) => void
  onReject: (id: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const showAlerts = needsAlertReview(suggestion.action_type) && alerts.length > 0

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <span className={styles.badge}>IA</span>
        <strong>{ACTION_TYPE_LABELS[suggestion.action_type]}</strong>
      </div>
      <p>{describeSuggestion(suggestion)}</p>

      {showAlerts && (
        <div className={styles.alertBox}>
          <strong>Alertas criticas del paciente:</strong>
          <ul>
            {alerts.map((alert) => (
              <li key={alert}>{alert}</li>
            ))}
          </ul>
        </div>
      )}

      {editing ? (
        <EditableFields
          payload={suggestion.payload}
          onCancel={() => setEditing(false)}
          onSave={(edits) => {
            setEditing(false)
            onAccept(suggestion.id, edits)
          }}
        />
      ) : (
        <div className={styles.cardActions}>
          <button
            className={styles.primaryButton}
            type="button"
            onClick={() => onAccept(suggestion.id)}
          >
            Aceptar
          </button>
          <button className={styles.secondaryButton} type="button" onClick={() => setEditing(true)}>
            Editar
          </button>
          <button
            className={styles.linkButton}
            type="button"
            onClick={() => onReject(suggestion.id)}
          >
            Rechazar
          </button>
        </div>
      )}
    </div>
  )
}

export function AiAssistant({
  patientId,
  encounterId,
  onInsertFallbackText,
}: {
  patientId: string
  encounterId: string
  onInsertFallbackText: (text: string) => void
}) {
  const queryClient = useQueryClient()
  const [micState, setMicState] = useState<MicState>('inactive')
  const [transcript, setTranscript] = useState('')
  const [unavailable, setUnavailable] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<BlobPart[]>([])

  const suggestionsQuery = useQuery({
    queryKey: ['ai-suggestions', encounterId],
    queryFn: () => api.listSuggestions(encounterId),
  })
  const alertsQuery = useQuery({
    queryKey: ['patient-alerts', patientId],
    queryFn: () => recordsApi.getPatientAlerts(patientId),
  })

  const pending = (suggestionsQuery.data ?? []).filter((s) => s.status === 'PENDING')

  const transcribeMutation = useMutation({
    mutationFn: (audio: Blob) => api.transcribe(audio),
    onSuccess: (data) => {
      setTranscript((prev) => (prev ? `${prev} ${data.text}` : data.text))
      setMicState('inactive')
    },
    onError: () => setMicState('inactive'),
  })

  const interpretMutation = useMutation({
    mutationFn: () => api.interpret(encounterId, transcript),
    onSuccess: () => {
      setUnavailable(false)
      queryClient.invalidateQueries({ queryKey: ['ai-suggestions', encounterId] })
    },
    onError: (error: unknown) => {
      if (error instanceof ApiRequestError && error.status === 503) setUnavailable(true)
    },
  })

  const acceptMutation = useMutation({
    mutationFn: ({ id, edits }: { id: string; edits?: Record<string, unknown> }) =>
      api.acceptSuggestion(id, edits),
    onSuccess: () => {
      // Aceptar una sugerencia puede escribir en expediente, odontograma,
      // diagnosticos o tratamiento segun el action_type (applier.py decide el
      // destino) -- se invalida todo lo que podria quedar desactualizado en esta
      // misma pantalla (p.ej. el motivo de consulta del encabezado) en vez de
      // intentar adivinar el destino exacto aqui.
      queryClient.invalidateQueries({ queryKey: ['ai-suggestions', encounterId] })
      queryClient.invalidateQueries({ queryKey: ['encounter', encounterId] })
      queryClient.invalidateQueries({ queryKey: ['patient-summary', patientId] })
      queryClient.invalidateQueries({ queryKey: ['patient-vital-signs', patientId] })
      queryClient.invalidateQueries({ queryKey: ['patient-allergies', patientId] })
      queryClient.invalidateQueries({ queryKey: ['patient-medications', patientId] })
      queryClient.invalidateQueries({ queryKey: ['patient-history', patientId] })
      queryClient.invalidateQueries({ queryKey: ['patient-diagnoses', patientId] })
      queryClient.invalidateQueries({ queryKey: ['odontogram', patientId] })
      queryClient.invalidateQueries({ queryKey: ['treatment-plans', patientId] })
      queryClient.invalidateQueries({ queryKey: ['patient-performed', patientId] })
      queryClient.invalidateQueries({ queryKey: ['patient-timeline', patientId] })
    },
  })

  const rejectMutation = useMutation({
    mutationFn: (id: string) => api.rejectSuggestion(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['ai-suggestions', encounterId] }),
  })

  async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const recorder = new MediaRecorder(stream)
    chunksRef.current = []
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data)
    }
    recorder.onstop = () => {
      stream.getTracks().forEach((track) => track.stop())
      const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
      setMicState('processing')
      transcribeMutation.mutate(blob)
    }
    recorder.start(5000)
    mediaRecorderRef.current = recorder
    setMicState('listening')
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop()
  }

  function toggleMic() {
    if (micState === 'inactive') {
      startRecording().catch(() => setMicState('inactive'))
    } else if (micState === 'listening') {
      stopRecording()
    }
  }

  useEffect(() => {
    function handleKeydown(e: KeyboardEvent) {
      if (e.altKey && e.key.toLowerCase() === 'm') {
        e.preventDefault()
        toggleMic()
      }
    }
    window.addEventListener('keydown', handleKeydown)
    return () => window.removeEventListener('keydown', handleKeydown)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [micState])

  const grouped = new Map<Destination, AiSuggestionOut[]>()
  for (const suggestion of pending) {
    const destination = ACTION_TYPE_DESTINATION[suggestion.action_type]
    grouped.set(destination, [...(grouped.get(destination) ?? []), suggestion])
  }

  const micLabel = {
    inactive: 'Dictar',
    listening: 'Escuchando... (clic para detener)',
    processing: 'Procesando...',
  }[micState]

  return (
    <section className={styles.panel}>
      <div className={styles.micRow}>
        <button
          type="button"
          className={`${styles.micButton} ${styles[micState]}`}
          onClick={toggleMic}
          disabled={micState === 'processing'}
          title="Alt+M"
        >
          🎙️ {micLabel}
        </button>
      </div>

      <textarea
        className={styles.transcript}
        placeholder="Transcripcion del dictado (editable)..."
        value={transcript}
        onChange={(e) => setTranscript(e.target.value)}
        rows={3}
      />

      <div className={styles.cardActions}>
        <button
          className={styles.primaryButton}
          type="button"
          disabled={!transcript.trim() || interpretMutation.isPending}
          onClick={() => interpretMutation.mutate()}
        >
          Interpretar dictado
        </button>
        {unavailable && (
          <button
            className={styles.secondaryButton}
            type="button"
            onClick={() => onInsertFallbackText(transcript)}
          >
            Insertar como texto en la nota
          </button>
        )}
      </div>

      {unavailable && (
        <p className={styles.errorBox}>
          El asistente de IA no esta disponible (Ollama no responde). La transcripcion si funciona:
          puedes insertarla como texto libre en la nota.
        </p>
      )}

      {interpretMutation.data && interpretMutation.data.unrecognized.length > 0 && (
        <div className={styles.unrecognizedBox}>
          <strong>No se pudo interpretar:</strong>
          <ul>
            {interpretMutation.data.unrecognized.map((item, i) => (
              <li key={i}>
                "{item.text}" — {item.reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      {pending.length > 0 && (
        <div className={styles.suggestionsHeader}>
          <h3>Propuestas del asistente</h3>
          <button
            className={styles.secondaryButton}
            type="button"
            onClick={() => pending.forEach((s) => acceptMutation.mutate({ id: s.id }))}
          >
            Aceptar todo
          </button>
        </div>
      )}

      {Array.from(grouped.entries()).map(([destination, items]) => (
        <div key={destination} className={styles.destinationGroup}>
          <h4>{destination}</h4>
          {items.map((suggestion) => (
            <SuggestionCard
              key={suggestion.id}
              suggestion={suggestion}
              alerts={alertsQuery.data ?? []}
              onAccept={(id, edits) => acceptMutation.mutate({ id, edits })}
              onReject={(id) => rejectMutation.mutate(id)}
            />
          ))}
        </div>
      ))}
    </section>
  )
}
