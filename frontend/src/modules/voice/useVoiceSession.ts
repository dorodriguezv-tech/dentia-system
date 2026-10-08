import { useEffect, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../auth/store'
import type { AudioCaptureHandle } from './audioCapture'
import { startAudioCapture } from './audioCapture'
import type { VoiceConnection } from './connection'
import { connectVoice } from './connection'
import { useScreenContextStore } from './screenContext'
import { useVoiceStore } from './store'
import { speak, stopSpeaking } from './ttsPlayer'
import type { VoiceServerMessage } from './types'

const CHANNEL_NAME = 'dentia-voice'
const LEADER_ELECTION_WINDOW_MS = 200

declare global {
  interface Window {
    // Fase 13.6 "Afinacion" (docs/06... C4): unico gancho para que un E2E de
    // Playwright controle una sesion de voz real con VOICE_FAKE_MODE=true
    // (manda {type:'fake_wake'}/{type:'fake_order', text}, ver
    // backend/app/voice/session.py) -- nunca existe en produccion.
    __dentiaTestSend?: (payload: unknown) => void
  }
}

type BroadcastPayload =
  | { type: 'claim'; tabId: string }
  | { type: 'leader'; tabId: string }
  | { type: 'leader-left'; tabId: string }

interface UseVoiceSessionDeps {
  connect?: typeof connectVoice
  startCapture?: typeof startAudioCapture
}

/** Orquesta la conexion de voz de Dentia (13.1 "Base de voz"): una sola pestana
 * tiene el microfono a la vez (coordinado por BroadcastChannel, sec. 7.1 del
 * diseno); las demas quedan en "activo en otra pestana". `deps` permite
 * inyectar dobles de conexion/captura en pruebas -- ninguno de los dos modulos
 * reales se puede probar de verdad en jsdom. */
export function useVoiceSession(deps: UseVoiceSessionDeps = {}): {
  toggleMute: () => void
} {
  const connectFn = deps.connect ?? connectVoice
  const startCaptureFn = deps.startCapture ?? startAudioCapture

  const accessToken = useAuthStore((s) => s.accessToken)
  const activeClinicId = useAuthStore((s) => s.activeClinicId)
  const setState = useVoiceStore((s) => s.setState)
  const setSubtitle = useVoiceStore((s) => s.setSubtitle)
  const setActiveInAnotherTab = useVoiceStore((s) => s.setActiveInAnotherTab)
  const navigate = useNavigate()
  const location = useLocation()
  const patientId = useScreenContextStore((s) => s.patientId)
  const encounterId = useScreenContextStore((s) => s.encounterId)
  const tab = useScreenContextStore((s) => s.tab)

  const connectionRef = useRef<VoiceConnection | null>(null)
  const captureRef = useRef<AudioCaptureHandle | null>(null)
  const capturingRef = useRef(false)
  const mutedRef = useRef(false)
  const toggleMuteRef = useRef<() => void>(() => {})
  // Espejo del contexto actual en un ref: handleMessage (dentro del efecto de
  // conexion, que no depende de patientId/encounterId/tab) lo necesita al
  // vuelo para mandar el contexto en cuanto se conecta, sin esperar a que el
  // efecto de abajo vuelva a correr.
  const contextRef = useRef({ route: location.pathname, patientId, encounterId, tab })

  function sendCurrentContext() {
    connectionRef.current?.send({
      type: 'context',
      route: contextRef.current.route,
      patient_id: contextRef.current.patientId,
      encounter_id: contextRef.current.encounterId,
      tab: contextRef.current.tab,
    })
  }

  useEffect(() => {
    if (!accessToken || !activeClinicId) {
      setState('disconnected')
      return
    }
    const token = accessToken
    const clinicId = activeClinicId

    let isLeader = false
    let stopped = false
    const tabId = Math.random().toString(36).slice(2)
    const channel = new BroadcastChannel(CHANNEL_NAME)

    function handleMessage(message: VoiceServerMessage) {
      if (message.type === 'state') {
        setState(message.state)
        if (message.state !== 'muted') mutedRef.current = false
        if (!capturingRef.current && message.state !== 'disconnected') {
          capturingRef.current = true
          sendCurrentContext()
          void startCaptureFn((frame) => connectionRef.current?.sendBinary(frame)).then(
            (handle) => {
              captureRef.current = handle
            },
          )
        }
      } else if (message.type === 'say') {
        setSubtitle(message.text)
        speak(message.text, message.audio)
      } else if (message.type === 'error') {
        console.error('[Dentia]', message.code, message.message)
        setState('disconnected')
      } else if (message.type === 'ui_action') {
        handleUiAction(message.action, message.payload)
      }
    }

    function handleUiAction(action: string, payload: Record<string, unknown>) {
      // 13.2 "Navegacion": solo "navigate" existe por ahora -- highlight_tooth,
      // open_modal, etc. llegan con las intenciones que los necesiten (13.3+).
      if (action === 'navigate' && typeof payload.path === 'string') {
        // La pestaña del paciente (si viene) es estado local de
        // PatientDetailPage, no parte de la URL -- se manda por location.state
        // y esa pantalla la lee al montar.
        const state = typeof payload.tab === 'string' ? { tab: payload.tab } : undefined
        navigate(payload.path, state ? { state } : undefined)
      }
    }

    function becomeLeader() {
      if (stopped || isLeader) return
      isLeader = true
      setActiveInAnotherTab(false)
      connectionRef.current = connectFn({
        token,
        clinicId,
        onMessage: handleMessage,
        onClose: () => setState('disconnected'),
      })
      if (import.meta.env.MODE !== 'production') {
        window.__dentiaTestSend = (payload) => connectionRef.current?.send(payload)
      }
      channel.postMessage({ type: 'leader', tabId } satisfies BroadcastPayload)
    }

    function stepDown() {
      if (!isLeader) return
      isLeader = false
      connectionRef.current?.close()
      connectionRef.current = null
      captureRef.current?.stop()
      captureRef.current = null
      capturingRef.current = false
      stopSpeaking()
      if (window.__dentiaTestSend) window.__dentiaTestSend = undefined
    }

    channel.onmessage = (event: MessageEvent<BroadcastPayload>) => {
      const payload = event.data
      if (payload.type === 'claim') {
        if (isLeader) channel.postMessage({ type: 'leader', tabId } satisfies BroadcastPayload)
      } else if (payload.type === 'leader' && payload.tabId !== tabId) {
        stepDown()
        setActiveInAnotherTab(true)
      } else if (payload.type === 'leader-left') {
        setActiveInAnotherTab(false)
        becomeLeader()
      }
    }

    channel.postMessage({ type: 'claim', tabId } satisfies BroadcastPayload)
    const electionTimer = setTimeout(() => {
      if (!stopped) becomeLeader()
    }, LEADER_ELECTION_WINDOW_MS)

    function handleBeforeUnload() {
      if (isLeader) channel.postMessage({ type: 'leader-left', tabId } satisfies BroadcastPayload)
    }
    window.addEventListener('beforeunload', handleBeforeUnload)

    function handleKeyDown(e: KeyboardEvent) {
      if (e.altKey && e.key.toLowerCase() === 'm') toggleMute()
    }
    window.addEventListener('keydown', handleKeyDown)

    function toggleMute() {
      if (!isLeader || !connectionRef.current) return
      mutedRef.current = !mutedRef.current
      connectionRef.current.send({ type: 'ui', action: mutedRef.current ? 'mute' : 'unmute' })
    }

    toggleMuteRef.current = toggleMute

    return () => {
      stopped = true
      clearTimeout(electionTimer)
      window.removeEventListener('beforeunload', handleBeforeUnload)
      window.removeEventListener('keydown', handleKeyDown)
      channel.onmessage = null
      channel.close()
      stepDown()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken, activeClinicId])

  // 13.2 "Navegacion": el cliente manda `context` cada vez que cambia la
  // pantalla (sec. 6.1 del diseno) -- efecto propio, independiente del ciclo
  // de vida de la conexion (arriba), para no reconectar el WebSocket solo
  // porque el usuario cambio de pestaña. (La primera vez que se conecta ya se
  // manda desde dentro de handleMessage, arriba, sin esperar a este efecto.)
  useEffect(() => {
    contextRef.current = { route: location.pathname, patientId, encounterId, tab }
    sendCurrentContext()
  }, [location.pathname, patientId, encounterId, tab])

  return { toggleMute: () => toggleMuteRef.current() }
}
