export type HistoryCategory =
  | 'heredofamiliar'
  | 'personal_patologico'
  | 'personal_no_patologico'
  | 'odontologico'
  | 'habito'
  | 'factor_riesgo'

export type Severity = 'leve' | 'moderada' | 'severa'

export const HISTORY_CATEGORY_LABELS: Record<HistoryCategory, string> = {
  heredofamiliar: 'Heredofamiliar',
  personal_patologico: 'Personal patologico',
  personal_no_patologico: 'Personal no patologico',
  odontologico: 'Odontologico',
  habito: 'Habito',
  factor_riesgo: 'Factor de riesgo',
}

export const SEVERITY_LABELS: Record<Severity, string> = {
  leve: 'Leve',
  moderada: 'Moderada',
  severa: 'Severa',
}

export interface MedicalHistoryOut {
  id: string
  encounter_id: string
  category: HistoryCategory
  text: string
  is_active: boolean
  created_at: string
}

export interface AllergyOut {
  id: string
  encounter_id: string
  substance: string
  reaction: string | null
  severity: Severity
  is_active: boolean
  created_at: string
}

export interface MedicationOut {
  id: string
  encounter_id: string
  name: string
  dose: string | null
  frequency: string | null
  is_active: boolean
  created_at: string
}

export interface VitalSignsOut {
  id: string
  encounter_id: string
  recorded_at: string
  bp_systolic: number | null
  bp_diastolic: number | null
  heart_rate: number | null
  temperature: number | null
}

export interface MedicalHistoryCreateInput {
  encounter_id: string
  category: HistoryCategory
  text: string
}

export interface AllergyCreateInput {
  encounter_id: string
  substance: string
  reaction?: string | null
  severity: Severity
}

export interface MedicationCreateInput {
  encounter_id: string
  name: string
  dose?: string | null
  frequency?: string | null
}

export interface VitalSignsCreateInput {
  encounter_id: string
  bp_systolic?: number | null
  bp_diastolic?: number | null
  heart_rate?: number | null
  temperature?: number | null
}
