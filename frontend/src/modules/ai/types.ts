export type ActionType =
  | 'set_chief_complaint'
  | 'add_allergy'
  | 'add_medication'
  | 'add_medical_history'
  | 'add_vital_signs'
  | 'add_tooth_finding'
  | 'add_planned_procedure'
  | 'add_performed_procedure'
  | 'add_diagnosis'
  | 'append_note'
  | 'schedule_followup'

export type SuggestionStatus = 'PENDING' | 'ACCEPTED' | 'REJECTED'

export interface TranscribeResponse {
  text: string
}

export interface UnrecognizedOut {
  text: string
  reason: string
}

export interface AiSuggestionOut {
  id: string
  batch_id: string
  encounter_id: string
  action_type: ActionType
  payload: Record<string, unknown>
  status: SuggestionStatus
  model_name: string
  model_digest: string | null
  transcript_excerpt: string | null
  created_at: string
  reviewed_at: string | null
  reject_reason: string | null
}

export interface InterpretResponse {
  suggestions: AiSuggestionOut[]
  unrecognized: UnrecognizedOut[]
}

export interface AiStatusOut {
  ai_enabled: boolean
  ollama_reachable: boolean
  ollama_model: string
  ollama_digest: string | null
  whisper_model: string
  whisper_device: string
}

export interface AiSettingsOut {
  ollama_model: string
  available_models: string[]
  ai_store_audio: boolean
}
