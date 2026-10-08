import styles from './DentiaOrb.module.css'
import { useVoiceSession } from './useVoiceSession'
import { useVoiceStore } from './store'

const STATE_LABELS: Record<string, string> = {
  disconnected: 'Dentia desconectada',
  passive: 'Dentia escuchando en segundo plano',
  awake: 'Dentia te escucha',
  listening: 'Dentia escuchando tu orden',
  thinking: 'Dentia pensando',
  speaking: 'Dentia hablando',
  confirming: 'Dentia espera tu confirmacion',
  muted: 'Microfono de Dentia apagado',
}

/** Fase 13 ("Dentia"), 13.1 "Base de voz": el orbe fijo de la esquina inferior
 * derecha (sec. 7 del diseno). Colores por estado via variables de tema
 * (CLAUDE.md sec. 6 -- nunca un #hex fijo), ver DentiaOrb.module.css. */
export function DentiaOrb() {
  const { toggleMute } = useVoiceSession()
  const state = useVoiceStore((s) => s.state)
  const subtitle = useVoiceStore((s) => s.subtitle)
  const activeInAnotherTab = useVoiceStore((s) => s.activeInAnotherTab)

  if (state === 'disconnected' && !activeInAnotherTab) return null

  const stateClass = activeInAnotherTab
    ? styles.otherTab
    : (styles[state] ?? styles.passive)
  const label = activeInAnotherTab ? 'Dentia activa en otra pestaña' : STATE_LABELS[state]

  return (
    <>
      {subtitle && !activeInAnotherTab && (
        <p className={styles.subtitle} role="status">
          {subtitle}
        </p>
      )}
      <button
        type="button"
        className={`${styles.orb} ${stateClass}`}
        aria-label={label}
        title={label}
        onClick={toggleMute}
        disabled={activeInAnotherTab}
      />
    </>
  )
}
