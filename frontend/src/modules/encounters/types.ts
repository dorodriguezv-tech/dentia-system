export type NoteStatus = 'DRAFT' | 'FINAL' | 'CORRECTED' | 'CANCELLED'

export const NOTE_STATUS_LABELS: Record<NoteStatus, string> = {
  DRAFT: 'Borrador',
  FINAL: 'Finalizada',
  CORRECTED: 'Corregida',
  CANCELLED: 'Cancelada',
}

export interface EncounterOut {
  id: string
  patient_id: string
  professional_id: string
  appointment_id: string | null
  chief_complaint: string | null
  started_at: string
  ended_at: string | null
}

export interface EncounterCreateInput {
  patient_id: string
  chief_complaint?: string | null
}

export interface ClinicalNoteOut {
  id: string
  encounter_id: string
  patient_id: string
  author_id: string
  status: NoteStatus
  soap_s: string | null
  soap_o: string | null
  soap_a: string | null
  soap_p: string | null
  free_text: string | null
  version: number
  previous_version_id: string | null
  correction_reason: string | null
  content_hash: string | null
  finalized_at: string | null
  cancel_reason: string | null
  updated_at: string
}

export interface ClinicalNoteFields {
  soap_s?: string | null
  soap_o?: string | null
  soap_a?: string | null
  soap_p?: string | null
  free_text?: string | null
}

export interface TimelineNoteOut {
  id: string
  status: NoteStatus
  version: number
  finalized_at: string | null
}

export interface TimelineEntryOut {
  encounter_id: string
  started_at: string
  chief_complaint: string | null
  professional_name: string
  notes: TimelineNoteOut[]
}
