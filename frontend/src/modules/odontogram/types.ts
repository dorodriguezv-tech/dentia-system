export type Surface = 'O' | 'M' | 'D' | 'V' | 'L' | 'P' | 'I'
export type Kind = 'EXISTING' | 'PLANNED' | 'PERFORMED'
export type Origin = 'MANUAL' | 'AI_ASSISTED'

export type FindingCode =
  | 'sano'
  | 'caries'
  | 'restauracion'
  | 'corona'
  | 'endodoncia'
  | 'ausente'
  | 'extraccion_indicada'
  | 'implante'
  | 'protesis_fija'
  | 'sellador'
  | 'fractura'
  | 'movilidad'

export interface ToothFindingOut {
  id: string
  encounter_id: string
  tooth_fdi: number
  surface: Surface | null
  finding_code: FindingCode
  kind: Kind
  material: string | null
  supersedes_id: string | null
  is_current: boolean
  origin: Origin
  created_at: string
}

export interface ToothFindingHistoryEntryOut extends ToothFindingOut {
  author_name: string
}

export interface ToothFindingCreateInput {
  patient_id: string
  encounter_id: string
  tooth_fdi: number
  surface?: Surface | null
  finding_code: FindingCode
  kind?: Kind
  material?: string | null
}

export type ViewMode = 'permanente' | 'temporal' | 'mixta'
