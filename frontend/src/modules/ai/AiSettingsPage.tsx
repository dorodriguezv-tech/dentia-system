import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as api from './api'
import styles from './AiSettingsPage.module.css'

function MicTest() {
  const [state, setState] = useState<'idle' | 'recording' | 'processing'>('idle')
  const [result, setResult] = useState<string | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<BlobPart[]>([])

  const transcribeMutation = useMutation({
    mutationFn: (audio: Blob) => api.transcribe(audio),
    onSuccess: (data) => {
      setResult(data.text || '(no se detecto texto)')
      setState('idle')
    },
    onError: () => setState('idle'),
  })

  async function start() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    const recorder = new MediaRecorder(stream)
    chunksRef.current = []
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data)
    }
    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop())
      setState('processing')
      transcribeMutation.mutate(new Blob(chunksRef.current, { type: 'audio/webm' }))
    }
    recorder.start()
    recorderRef.current = recorder
    setState('recording')
  }

  function stop() {
    recorderRef.current?.stop()
  }

  return (
    <div className={styles.micTest}>
      <button
        className={styles.secondaryButton}
        type="button"
        disabled={state === 'processing'}
        onClick={() => (state === 'recording' ? stop() : start().catch(() => setState('idle')))}
      >
        {state === 'idle' && 'Probar microfono'}
        {state === 'recording' && 'Detener prueba'}
        {state === 'processing' && 'Procesando...'}
      </button>
      {result !== null && <p>Transcripcion: "{result}"</p>}
    </div>
  )
}

export function AiSettingsPage() {
  const queryClient = useQueryClient()
  const statusQuery = useQuery({ queryKey: ['ai-status'], queryFn: api.getStatus })
  const settingsQuery = useQuery({ queryKey: ['ai-settings'], queryFn: api.getSettings })
  const [selectedModel, setSelectedModel] = useState<string | null>(null)

  const updateMutation = useMutation({
    mutationFn: (model: string) => api.updateSettings(model),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-settings'] })
      queryClient.invalidateQueries({ queryKey: ['ai-status'] })
    },
  })

  if (statusQuery.isLoading || settingsQuery.isLoading) {
    return <p>Cargando configuracion del asistente...</p>
  }
  if (!statusQuery.data || !settingsQuery.data) {
    return <p>No se pudo cargar la configuracion del asistente.</p>
  }

  const status = statusQuery.data
  const settings = settingsQuery.data
  const model = selectedModel ?? settings.ollama_model

  return (
    <section className={styles.page}>
      <h1>Asistente de IA</h1>

      <div className={styles.card}>
        <h2>Estado</h2>
        <dl className={styles.statusGrid}>
          <dt>Ollama</dt>
          <dd className={status.ollama_reachable ? styles.ok : styles.down}>
            {status.ollama_reachable ? 'Conectado' : 'No disponible'}
          </dd>
          <dt>Modelo</dt>
          <dd>{status.ollama_model}</dd>
          <dt>Digest</dt>
          <dd>{status.ollama_digest ?? '-'}</dd>
          <dt>Whisper</dt>
          <dd>
            {status.whisper_model} ({status.whisper_device})
          </dd>
        </dl>
      </div>

      <div className={styles.card}>
        <h2>Modelo de Ollama</h2>
        {settings.available_models.length === 0 ? (
          <p>No hay modelos instalados en Ollama o no esta disponible.</p>
        ) : (
          <>
            <select value={model} onChange={(e) => setSelectedModel(e.target.value)}>
              {settings.available_models.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
            <button
              className={styles.primaryButton}
              type="button"
              disabled={updateMutation.isPending || model === settings.ollama_model}
              onClick={() => updateMutation.mutate(model)}
            >
              Guardar
            </button>
          </>
        )}
      </div>

      <div className={styles.card}>
        <h2>Microfono</h2>
        <MicTest />
      </div>

      <div className={styles.card}>
        <h2>Privacidad</h2>
        <label className={styles.checkboxRow}>
          <input type="checkbox" checked={settings.ai_store_audio} disabled />
          <span>
            Guardar audio de los dictados (desactivado por privacidad; se cambia en el .env del
            servidor con AI_STORE_AUDIO)
          </span>
        </label>
      </div>
    </section>
  )
}
