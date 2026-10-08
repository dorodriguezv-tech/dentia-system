import { API_BASE_URL } from '../../api/client'
import type { VoiceServerMessage } from './types'

/** Convierte la URL http(s) de la API en la del WebSocket de voz. */
export function voiceWebSocketUrl(): string {
  const wsBase = API_BASE_URL.replace(/^http/, 'ws')
  return `${wsBase}/voice/ws`
}

export interface VoiceConnection {
  send: (payload: unknown) => void
  sendBinary: (data: ArrayBuffer) => void
  close: () => void
}

export interface VoiceConnectionOptions {
  token: string
  clinicId: string
  onMessage: (message: VoiceServerMessage) => void
  onClose: () => void
}

/** Thin wrapper sobre WebSocket nativo -- aislado en su propio modulo para que
 * useVoiceSession.ts pueda sustituirlo por un doble en pruebas, igual que
 * audioCapture.ts (ninguno de los dos se puede probar de verdad en jsdom). */
export function connectVoice(options: VoiceConnectionOptions): VoiceConnection {
  const ws = new WebSocket(voiceWebSocketUrl())
  ws.binaryType = 'arraybuffer'

  ws.onopen = () => {
    ws.send(JSON.stringify({ type: 'auth', token: options.token, clinic_id: options.clinicId }))
  }

  ws.onmessage = (event) => {
    if (typeof event.data !== 'string') return
    try {
      const message = JSON.parse(event.data) as VoiceServerMessage
      options.onMessage(message)
    } catch {
      // mensaje malformado: se ignora, no se interrumpe la conexion.
    }
  }

  ws.onclose = () => options.onClose()
  ws.onerror = () => {
    // onclose se dispara igual despues de un error de WebSocket.
  }

  return {
    send: (payload) => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload))
    },
    sendBinary: (data) => {
      if (ws.readyState === WebSocket.OPEN) ws.send(data)
    },
    close: () => ws.close(),
  }
}
