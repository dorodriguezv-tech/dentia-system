import { useEffect } from 'react'
import { useErrorToastStore } from './errorToastStore'
import styles from './ErrorToast.module.css'

const AUTO_DISMISS_MS = 8000

/** A4: ultima red para que un error de cualquier mutacion (vea app/providers.tsx)
 * siempre se vea en pantalla, nunca en silencio. */
export function ErrorToast() {
  const message = useErrorToastStore((s) => s.message)
  const dismiss = useErrorToastStore((s) => s.dismiss)

  useEffect(() => {
    if (!message) return
    const timeout = setTimeout(dismiss, AUTO_DISMISS_MS)
    return () => clearTimeout(timeout)
  }, [message, dismiss])

  if (!message) return null

  return (
    <div className={styles.toast} role="alert">
      <span className={styles.message}>{message}</span>
      <button className={styles.closeButton} type="button" onClick={dismiss} aria-label="Cerrar">
        ×
      </button>
    </div>
  )
}
