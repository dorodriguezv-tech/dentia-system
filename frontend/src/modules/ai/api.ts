import { apiRequest, apiRequestFormData } from '../../api/client'
import type {
  AiSettingsOut,
  AiStatusOut,
  AiSuggestionOut,
  InterpretResponse,
  TranscribeResponse,
} from './types'

export async function transcribe(audio: Blob): Promise<TranscribeResponse> {
  const formData = new FormData()
  formData.append('audio', audio, 'dictado.webm')
  return apiRequestFormData<TranscribeResponse>('/ai/transcribe', formData)
}

export async function interpret(encounterId: string, transcript: string): Promise<InterpretResponse> {
  return apiRequest<InterpretResponse>('/ai/interpret', {
    method: 'POST',
    body: { encounter_id: encounterId, transcript },
  })
}

export async function listSuggestions(encounterId: string): Promise<AiSuggestionOut[]> {
  return apiRequest<AiSuggestionOut[]>(`/ai/suggestions?encounter_id=${encounterId}`)
}

export async function acceptSuggestion(
  suggestionId: string,
  edits?: Record<string, unknown>,
): Promise<AiSuggestionOut> {
  return apiRequest<AiSuggestionOut>(`/ai/suggestions/${suggestionId}/accept`, {
    method: 'POST',
    body: { edits: edits ?? null },
  })
}

export async function rejectSuggestion(suggestionId: string, reason?: string): Promise<AiSuggestionOut> {
  return apiRequest<AiSuggestionOut>(`/ai/suggestions/${suggestionId}/reject`, {
    method: 'POST',
    body: { reason: reason ?? null },
  })
}

export async function getStatus(): Promise<AiStatusOut> {
  return apiRequest<AiStatusOut>('/ai/status')
}

export async function getSettings(): Promise<AiSettingsOut> {
  return apiRequest<AiSettingsOut>('/ai/settings')
}

export async function updateSettings(ollamaModel: string): Promise<AiSettingsOut> {
  return apiRequest<AiSettingsOut>('/ai/settings', {
    method: 'PUT',
    body: { ollama_model: ollamaModel },
  })
}
