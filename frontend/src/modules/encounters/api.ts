import { apiRequest } from '../../api/client'
import type {
  ClinicalNoteFields,
  ClinicalNoteOut,
  EncounterCreateInput,
  EncounterOut,
  TimelineEntryOut,
} from './types'

export function createEncounter(input: EncounterCreateInput): Promise<EncounterOut> {
  return apiRequest<EncounterOut>('/encounters', { method: 'POST', body: input })
}

export function getEncounter(encounterId: string): Promise<EncounterOut> {
  return apiRequest<EncounterOut>(`/encounters/${encounterId}`)
}

export function listPatientEncounters(patientId: string): Promise<EncounterOut[]> {
  return apiRequest<EncounterOut[]>(`/patients/${patientId}/encounters`)
}

export function getPatientTimeline(patientId: string): Promise<TimelineEntryOut[]> {
  return apiRequest<TimelineEntryOut[]>(`/patients/${patientId}/timeline`)
}

export function createNote(
  encounterId: string,
  input: ClinicalNoteFields,
): Promise<ClinicalNoteOut> {
  return apiRequest<ClinicalNoteOut>(`/encounters/${encounterId}/notes`, {
    method: 'POST',
    body: input,
  })
}

export function listEncounterNotes(encounterId: string): Promise<ClinicalNoteOut[]> {
  return apiRequest<ClinicalNoteOut[]>(`/encounters/${encounterId}/notes`)
}

export function getNote(noteId: string): Promise<ClinicalNoteOut> {
  return apiRequest<ClinicalNoteOut>(`/notes/${noteId}`)
}

export function updateNote(noteId: string, input: ClinicalNoteFields): Promise<ClinicalNoteOut> {
  return apiRequest<ClinicalNoteOut>(`/notes/${noteId}`, { method: 'PATCH', body: input })
}

export function finalizeNote(
  noteId: string,
  alertsAcknowledged: boolean,
): Promise<ClinicalNoteOut> {
  return apiRequest<ClinicalNoteOut>(`/notes/${noteId}/finalize`, {
    method: 'POST',
    body: { alerts_acknowledged: alertsAcknowledged },
  })
}

export function correctNote(noteId: string, reason: string): Promise<ClinicalNoteOut> {
  return apiRequest<ClinicalNoteOut>(`/notes/${noteId}/correct`, {
    method: 'POST',
    body: { reason },
  })
}

export function cancelNote(noteId: string, reason: string): Promise<ClinicalNoteOut> {
  return apiRequest<ClinicalNoteOut>(`/notes/${noteId}/cancel`, {
    method: 'POST',
    body: { reason },
  })
}
