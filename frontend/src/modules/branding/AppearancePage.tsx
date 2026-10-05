import { useEffect, useRef, useState, type ChangeEvent } from 'react'
import { resolveApiAssetUrl } from '../../api/client'
import { useAuthStore } from '../auth/store'
import { useThemeStore } from '../../theme/store'
import { BUTTON_TEXT_COLOR, meetsContrast } from '../../theme/colorUtils'
import { PRESETS, fullPalette } from '../../theme/presets'
import * as api from './api'
import styles from './AppearancePage.module.css'
import type { BrandingOut, ColorPalette, RadiusCode } from './types'

const EDITABLE_COLOR_FIELDS: { key: keyof ColorPalette; label: string }[] = [
  { key: 'primary', label: 'Primario' },
  { key: 'secondary', label: 'Secundario' },
  { key: 'accent', label: 'Acento' },
  { key: 'bg', label: 'Fondo' },
]

export function AppearancePage() {
  const branding = useThemeStore((s) => s.branding)

  if (!branding) {
    return <p>Cargando apariencia...</p>
  }

  return <AppearanceForm initial={branding} />
}

function AppearanceForm({ initial }: { initial: BrandingOut }) {
  const applyPreview = useThemeStore((s) => s.applyPreview)
  const applySaved = useThemeStore((s) => s.applySaved)
  const resetPreviewToSaved = useThemeStore((s) => s.resetPreviewToSaved)

  const accessToken = useAuthStore((s) => s.accessToken)
  const activeClinicId = useAuthStore((s) => s.activeClinicId)

  const [displayName, setDisplayName] = useState(initial.display_name)
  const [subtitle, setSubtitle] = useState(initial.subtitle ?? '')
  const [preset, setPreset] = useState(initial.preset)
  const [colors, setColors] = useState<ColorPalette>(initial.colors)
  const [darkMode, setDarkMode] = useState(initial.dark_mode)
  const [radius, setRadius] = useState<RadiusCode>(initial.radius)
  const [logoUrl, setLogoUrl] = useState(initial.logo_url)
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [message, setMessage] = useState<{ kind: 'success' | 'error'; text: string } | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    applyPreview(colors, darkMode, radius)
  }, [colors, darkMode, radius, applyPreview])

  useEffect(() => resetPreviewToSaved, [resetPreviewToSaved])

  function handlePresetSelect(code: string) {
    setPreset(code)
    setColors(fullPalette(code))
  }

  function handleColorChange(key: keyof ColorPalette, value: string) {
    setPreset('custom')
    setColors((prev) => ({ ...prev, [key]: value }))
  }

  async function handleSave() {
    setSaving(true)
    setMessage(null)
    try {
      const result = await api.updateBranding({
        display_name: displayName,
        subtitle: subtitle || null,
        preset,
        colors: preset === 'custom' ? colors : undefined,
        dark_mode: darkMode,
        radius,
      })
      applySaved(result)
      if (result.contrast_warnings.length > 0) {
        setMessage({
          kind: 'error',
          text: `Guardado, pero hay contraste insuficiente en: ${result.contrast_warnings
            .map((w) => w.pair)
            .join(', ')}.`,
        })
      } else {
        setMessage({ kind: 'success', text: 'Apariencia guardada.' })
      }
    } catch {
      setMessage({ kind: 'error', text: 'No se pudo guardar la apariencia.' })
    } finally {
      setSaving(false)
    }
  }

  function handleReset() {
    setDisplayName(initial.display_name)
    setSubtitle(initial.subtitle ?? '')
    setPreset(initial.preset)
    setColors(initial.colors)
    setDarkMode(initial.dark_mode)
    setRadius(initial.radius)
    setMessage(null)
  }

  async function handleLogoSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file || !accessToken || !activeClinicId) return

    setUploading(true)
    setMessage(null)
    try {
      const result = await api.uploadLogo(file, accessToken, activeClinicId)
      applySaved(result)
      setLogoUrl(result.logo_url)
      setMessage({ kind: 'success', text: 'Logo actualizado.' })
    } catch (err) {
      setMessage({
        kind: 'error',
        text: err instanceof Error ? err.message : 'No se pudo subir el logo',
      })
    } finally {
      setUploading(false)
    }
  }

  const textContrastOk = meetsContrast(colors.text, colors.bg)
  const buttonContrastOk = meetsContrast(BUTTON_TEXT_COLOR, colors.primary)

  return (
    <section>
      <h1>Apariencia</h1>

      {message && (
        <div className={message.kind === 'success' ? styles.successBox : styles.warningBox}>
          {message.text}
        </div>
      )}

      <div className={styles.layout}>
        <div className={styles.panel}>
          <div className={styles.field}>
            <label htmlFor="display_name">Nombre comercial</label>
            <input
              id="display_name"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </div>

          <div className={styles.field}>
            <label htmlFor="subtitle">Subtitulo</label>
            <input
              id="subtitle"
              type="text"
              value={subtitle}
              onChange={(e) => setSubtitle(e.target.value)}
            />
          </div>

          <div className={styles.field}>
            <label>Logo</label>
            <div className={styles.logoPreview}>
              {logoUrl && <img src={resolveApiAssetUrl(logoUrl)} alt="Logo actual" />}
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                {uploading ? 'Subiendo...' : 'Cambiar logo'}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/svg+xml"
                hidden
                onChange={handleLogoSelected}
              />
            </div>
          </div>

          <div className={styles.field}>
            <label>Preset</label>
            <div className={styles.presetGrid}>
              {PRESETS.map((p) => (
                <button
                  key={p.code}
                  type="button"
                  className={`${styles.presetButton} ${preset === p.code ? styles.active : ''}`}
                  onClick={() => handlePresetSelect(p.code)}
                >
                  <div className={styles.swatches}>
                    {[p.primary, p.secondary, p.accent].map((c) => (
                      <span key={c} className={styles.swatch} style={{ backgroundColor: c }} />
                    ))}
                  </div>
                  {p.name}
                </button>
              ))}
            </div>
          </div>

          <div className={styles.field}>
            <label>Personalizar colores</label>
            <div className={styles.colorGrid}>
              {EDITABLE_COLOR_FIELDS.map(({ key, label }) => (
                <label key={key} className={styles.colorField}>
                  <input
                    type="color"
                    value={colors[key]}
                    onChange={(e) => handleColorChange(key, e.target.value)}
                  />
                  {label}
                </label>
              ))}
            </div>
            {!textContrastOk && (
              <p className={styles.warningBox}>Poco contraste entre el texto y el fondo.</p>
            )}
            {!buttonContrastOk && (
              <p className={styles.warningBox}>Poco contraste entre el boton y su texto.</p>
            )}
          </div>

          <div className={styles.toggleRow}>
            <label htmlFor="dark_mode">Modo oscuro</label>
            <input
              id="dark_mode"
              type="checkbox"
              checked={darkMode}
              onChange={(e) => setDarkMode(e.target.checked)}
            />
          </div>

          <div className={styles.field}>
            <label>Radio de bordes</label>
            <div className={styles.radiusOptions}>
              <button
                type="button"
                className={radius === 'soft' ? styles.active : ''}
                onClick={() => setRadius('soft')}
              >
                Suave
              </button>
              <button
                type="button"
                className={radius === 'sharp' ? styles.active : ''}
                onClick={() => setRadius('sharp')}
              >
                Recto
              </button>
            </div>
          </div>

          <div className={styles.actions}>
            <button
              type="button"
              className={styles.primaryButton}
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? 'Guardando...' : 'Guardar'}
            </button>
            <button type="button" className={styles.secondaryButton} onClick={handleReset}>
              Restablecer
            </button>
          </div>
        </div>

        <div>
          <p className={styles.previewHeading}>Vista previa</p>
          <div className={styles.previewGrid}>
            <div className={styles.previewSidebar}>
              <div className={styles.previewBrand}>{displayName || 'DentalCare'}</div>
              <div className={styles.previewNavItem}>Inicio</div>
              <div className={styles.previewNavItem}>Pacientes</div>
            </div>
            <div className={styles.previewMain}>
              <div className={styles.previewCard}>
                <strong>Tarjeta de ejemplo</strong>
                <p>Asi se ve el contenido con estos colores.</p>
              </div>
              <button type="button" className={styles.previewButton}>
                Boton primario
              </button>
              <div className={styles.previewAlert}>Alerta: paciente alergico a la penicilina.</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
