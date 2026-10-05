import type { Surface } from '../odontogram/types'

export type DiagnosisCode =
  | 'caries'
  | 'caries_recurrente'
  | 'pulpitis_reversible'
  | 'pulpitis_irreversible'
  | 'necrosis_pulpar'
  | 'absceso_periapical'
  | 'gingivitis'
  | 'periodontitis'
  | 'fractura_dental'
  | 'edentulismo_parcial'
  | 'maloclusion'
  | 'sin_hallazgos'

export interface DiagnosisOut {
  id: string
  encounter_id: string
  professional_id: string
  tooth_fdi: number | null
  surface: Surface | null
  code: DiagnosisCode | null
  text: string
  is_active: boolean
  created_at: string
}

export interface DiagnosisCreateInput {
  encounter_id: string
  tooth_fdi?: number | null
  surface?: Surface | null
  code?: DiagnosisCode | null
  text: string
}
