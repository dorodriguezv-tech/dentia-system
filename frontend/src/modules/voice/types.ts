/** Fase 13 ("Dentia"). Copia minima de los mensajes del WebSocket que ya
 * existen en backend/app/voice/session.py (fuente de verdad real). 13.1:
 * state/say/error, mute/unmute y auth. 13.2 "Navegacion" agrega context
 * (pantalla actual) y ui_action (navigate por ahora; highlight_tooth,
 * open_modal, etc. llegan con las intenciones que los necesiten). card,
 * applied/undone y transcript siguen sin usarse -- son del dialogo con
 * confirmacion (13.3+). */

export type VoiceConnectionState =
  | 'disconnected'
  | 'passive'
  | 'awake'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'confirming'
  | 'muted'

export interface VoiceStateMessage {
  type: 'state'
  state: VoiceConnectionState
}

export interface VoiceSayMessage {
  type: 'say'
  text: string
  audio: string | null
}

export interface VoiceErrorMessage {
  type: 'error'
  code: string
  message: string
}

export interface VoiceUiActionMessage {
  type: 'ui_action'
  action: string
  payload: Record<string, unknown>
}

export type VoiceServerMessage =
  | VoiceStateMessage
  | VoiceSayMessage
  | VoiceErrorMessage
  | VoiceUiActionMessage

export interface VoiceAuthMessage {
  type: 'auth'
  token: string
  clinic_id: string
}

export interface VoiceUiMessage {
  type: 'ui'
  action: 'mute' | 'unmute'
}

export interface VoiceContextMessage {
  type: 'context'
  route: string | null
  patient_id: string | null
  encounter_id: string | null
  tab: string | null
}

export interface VoiceFakeWakeMessage {
  type: 'fake_wake'
}

export interface VoiceFakeOrderMessage {
  type: 'fake_order'
  text: string
}
