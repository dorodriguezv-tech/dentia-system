export type StudyType =
  | 'intraoral'
  | 'extraoral'
  | 'periapical'
  | 'bitewing'
  | 'panoramica'
  | 'cefalometria'

export interface ImageOut {
  id: string
  encounter_id: string
  study_type: StudyType
  tooth_fdi: number | null
  procedure_planned_id: string | null
  procedure_performed_id: string | null
  content_type: string
  original_filename: string
  notes: string | null
  has_thumbnail: boolean
  is_active: boolean
  created_at: string
}

export interface ImageUploadInput {
  encounter_id: string
  study_type: StudyType
  tooth_fdi: number | null
  notes: string | null
  files: File[]
}
