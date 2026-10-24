import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from './store'

// PDF "Guia de publicacion en ambiente web" sec. 5, bloqueante #6: con el sistema
// expuesto a internet, una sesion olvidada abierta (p. ej. en una computadora
// compartida de la clinica) queda vulnerable mas alla del access token de 15 min,
// porque el refresh token (8 h) la va renovando sola en segundo plano.
const INACTIVITY_TIMEOUT_MS = 15 * 60 * 1000

const ACTIVITY_EVENTS = ['mousedown', 'keydown', 'touchstart', 'scroll'] as const

/** Cierra la sesion si no hay actividad del usuario por INACTIVITY_TIMEOUT_MS.
 * Montar una sola vez, dentro del shell autenticado (ver app/Layout.tsx). */
export function useInactivityLogout() {
  const navigate = useNavigate()
  const status = useAuthStore((s) => s.status)

  useEffect(() => {
    if (status !== 'authenticated') return

    let timer: ReturnType<typeof setTimeout>

    function handleTimeout() {
      void useAuthStore.getState().logout()
      navigate('/login')
    }

    function resetTimer() {
      clearTimeout(timer)
      timer = setTimeout(handleTimeout, INACTIVITY_TIMEOUT_MS)
    }

    resetTimer()
    for (const event of ACTIVITY_EVENTS) window.addEventListener(event, resetTimer)

    return () => {
      clearTimeout(timer)
      for (const event of ACTIVITY_EVENTS) window.removeEventListener(event, resetTimer)
    }
  }, [status, navigate])
}
