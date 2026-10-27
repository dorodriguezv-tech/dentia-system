import { useEffect, useRef, useState, type ChangeEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiRequestBlobUrl } from '../../api/client'
import * as api from './api'
import styles from './DocumentSettingsPage.module.css'
import type { DocumentSettingsOut, LogoSide } from './types'

/**
 * A diferencia del logo de Marca y Temas (publico, `apiRequest(..., { auth: false })`
 * + `<img src>` directo), los logos de Formatos de documentos exigen sesion y
 * sucursal activa (`GET /document-settings/logo-{side}` pide `get_current_user` +
 * `X-Clinic-Id`, ver backend/app/modules/document_settings/router.py) -- un
 * `<img>` normal no puede mandar esos encabezados. Mismo patron que la foto del
 * paciente (PatientHeader.tsx::usePhotoUrl): pedir el binario con fetch
 * autenticado y convertirlo a blob URL.
 */
function useLogoUrl(side: LogoSide, hasLogo: boolean, version: number): string | null {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!hasLogo) return

    let objectUrl: string | null = null
    let cancelled = false
    apiRequestBlobUrl(`/document-settings/logo-${side}`).then((u) => {
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
  }, [side, hasLogo, version])

  return url
}

function LogoUploadField({
  side,
  label,
  hasLogo,
  version,
  onUploaded,
}: {
  side: LogoSide
  label: string
  hasLogo: boolean
  version: number
  onUploaded: (result: DocumentSettingsOut) => void
}) {
  const logoUrl = useLogoUrl(side, hasLogo, version)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [error, setError] = useState<string | null>(null)

  const uploadMutation = useMutation({
    mutationFn: (file: File) => api.uploadLogo(side, file),
    onSuccess: (result) => {
      setError(null)
      onUploaded(result)
    },
    onError: () => setError('No se pudo subir el logo.'),
  })

  function handleSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    uploadMutation.mutate(file)
  }

  return (
    <div className={styles.field}>
      <label>{label}</label>
      <div className={styles.logoPreview}>
        {logoUrl ? (
          <img src={logoUrl} alt={label} />
        ) : (
          <div className={styles.logoPlaceholder}>Sin logo</div>
        )}
        <button
          type="button"
          className={styles.secondaryButton}
          onClick={() => fileInputRef.current?.click()}
          disabled={uploadMutation.isPending}
        >
          {uploadMutation.isPending ? 'Subiendo...' : 'Cambiar logo'}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/svg+xml"
          hidden
          onChange={handleSelected}
        />
      </div>
      {error && <p className={styles.errorBox}>{error}</p>}
    </div>
  )
}

export function DocumentSettingsPage() {
  const settingsQuery = useQuery({
    queryKey: ['document-settings'],
    queryFn: api.getDocumentSettings,
  })

  if (settingsQuery.isLoading) {
    return <p>Cargando formatos de documentos...</p>
  }
  if (settingsQuery.isError || !settingsQuery.data) {
    return <p>No se pudieron cargar los formatos de documentos.</p>
  }

  return <DocumentSettingsForm initial={settingsQuery.data} />
}

/** Mismo patron que branding/AppearancePage.tsx::AppearanceForm: el estado local se
 * inicializa una sola vez desde `initial` (prop), sin useEffect, para no disparar
 * renders en cascada (react-hooks/set-state-in-effect). */
function DocumentSettingsForm({ initial }: { initial: DocumentSettingsOut }) {
  const queryClient = useQueryClient()
  const [settings, setSettings] = useState(initial)
  const [institutionalTitle, setInstitutionalTitle] = useState(initial.institutional_title ?? '')
  const [placeLabel, setPlaceLabel] = useState(initial.place_label ?? '')
  const [message, setMessage] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)
  // Fuerza a useLogoUrl a volver a pedir el binario tras subir un logo nuevo
  // (hasLogo no cambia de true a true, asi que no dispara el efecto por si solo).
  const [logoVersion, setLogoVersion] = useState(0)

  function applyResult(result: DocumentSettingsOut) {
    setSettings(result)
    queryClient.setQueryData(['document-settings'], result)
  }

  const saveMutation = useMutation({
    mutationFn: () =>
      api.updateDocumentSettings({
        institutional_title: institutionalTitle || null,
        place_label: placeLabel || null,
      }),
    onSuccess: (result) => {
      applyResult(result)
      setMessage({ kind: 'success', text: 'Formatos de documentos guardados.' })
    },
    onError: () => setMessage({ kind: 'error', text: 'No se pudo guardar.' }),
  })

  return (
    <section>
      <h1>Formatos de documentos</h1>
      <p className={styles.description}>
        El logo izquierdo, el logo derecho, el título institucional y el lugar
        configurados aquí se usan en el encabezado de todos los documentos
        imprimibles (historias clínicas, consentimientos, recetas, referencias,
        etc.).
      </p>

      {message && (
        <div className={message.kind === 'success' ? styles.successBox : styles.errorBox}>
          {message.text}
        </div>
      )}

      <div className={styles.panel}>
        <div className={styles.logosRow}>
          <LogoUploadField
            side="left"
            label="Logo izquierdo"
            hasLogo={settings.has_logo_left}
            version={logoVersion}
            onUploaded={(result) => {
              applyResult(result)
              setLogoVersion((v) => v + 1)
            }}
          />
          <LogoUploadField
            side="right"
            label="Logo derecho"
            hasLogo={settings.has_logo_right}
            version={logoVersion}
            onUploaded={(result) => {
              applyResult(result)
              setLogoVersion((v) => v + 1)
            }}
          />
        </div>

        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            saveMutation.mutate()
          }}
        >
          <div className={styles.field}>
            <label htmlFor="institutional_title">Título institucional</label>
            <input
              id="institutional_title"
              type="text"
              placeholder="Razón social o título que aparece en el encabezado impreso"
              value={institutionalTitle}
              onChange={(e) => setInstitutionalTitle(e.target.value)}
            />
          </div>
          <div className={styles.field}>
            <label htmlFor="place_label">Lugar</label>
            <input
              id="place_label"
              type="text"
              placeholder="Ciudad para 'Lugar y fecha' en los documentos impresos"
              value={placeLabel}
              onChange={(e) => setPlaceLabel(e.target.value)}
            />
          </div>
          <div className={styles.actions}>
            <button
              className={styles.primaryButton}
              type="submit"
              disabled={saveMutation.isPending}
            >
              {saveMutation.isPending ? 'Guardando...' : 'Guardar'}
            </button>
          </div>
        </form>
      </div>
    </section>
  )
}
