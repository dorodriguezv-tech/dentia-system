import type { FindingCode, Surface } from '../odontogram/types'

export type PlanStatus =
  | 'BORRADOR'
  | 'PRESENTADO'
  | 'ACEPTADO'
  | 'RECHAZADO'
  | 'EN_PROGRESO'
  | 'TERMINADO'

export type Priority = 'alta' | 'media' | 'baja'
export type AcceptanceType = 'TOTAL' | 'PARCIAL'

export interface ProcedureCatalogOut {
  id: string
  code: string
  name: string
  default_price: string
  is_active: boolean
}

export interface ProcedureCatalogCreateInput {
  code: string
  name: string
  default_price: string
}

export interface PlanOut {
  id: string
  patient_id: string
  encounter_id: string
  professional_id: string
  professional_name: string
  title: string
  status: PlanStatus
  notes: string | null
  accepted_at: string | null
  accepted_by_name: string | null
  acceptance_type: AcceptanceType | null
  rejected_reason: string | null
  total: string
}

export interface PlanCreateInput {
  patient_id: string
  encounter_id: string
  title: string
  notes?: string | null
}

export interface ItemOut {
  id: string
  phase_id: string
  encounter_id: string
  tooth_fdi: number | null
  surface: Surface | null
  procedure_code: string
  procedure_name: string
  finding_code: FindingCode | null
  unit_price: string
  quantity: number
  alternative: string
  discount_amount: string | null
  discount_reason: string | null
  accepted: boolean
  is_active: boolean
  subtotal: string
}

export interface ItemCreateInput {
  encounter_id: string
  tooth_fdi?: number | null
  surface?: Surface | null
  procedure_code: string
  finding_code?: FindingCode | null
  quantity?: number
  alternative?: string
  unit_price_override?: string | null
}

export interface PhaseWithItemsOut {
  id: string
  name: string
  sort_order: number
  priority: Priority
  items: ItemOut[]
  phase_total: string
}

export interface PhaseCreateInput {
  name: string
  sort_order?: number
  priority?: Priority
}

export interface PlanDetailOut {
  id: string
  patient_id: string
  encounter_id: string
  professional_id: string
  professional_name: string
  title: string
  status: PlanStatus
  notes: string | null
  accepted_at: string | null
  accepted_by_name: string | null
  acceptance_type: AcceptanceType | null
  rejected_reason: string | null
  phases: PhaseWithItemsOut[]
  total: string
}

export interface ProcedurePerformedOut {
  id: string
  patient_id: string
  encounter_id: string
  planned_id: string | null
  professional_name: string
  tooth_fdi: number | null
  surface: Surface | null
  procedure_code: string
  procedure_name: string
  material: string | null
  performed_at: string
  charge_amount: string
}

export interface ProcedurePerformedCreateInput {
  patient_id: string
  encounter_id: string
  planned_id?: string | null
  tooth_fdi?: number | null
  surface?: Surface | null
  procedure_code?: string | null
  procedure_name?: string | null
  finding_code?: FindingCode | null
  material?: string | null
}
