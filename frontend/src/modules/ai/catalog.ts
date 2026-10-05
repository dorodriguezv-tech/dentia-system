import { DIAGNOSIS_CATALOG } from '../diagnosis/catalog'
import { FINDING_CATALOG } from '../odontogram/findingCatalog'
import type { FindingCode } from '../odontogram/types'
import type { DiagnosisCode } from '../diagnosis/types'
import type { ActionType, AiSuggestionOut } from './types'

export const ACTION_TYPE_LABELS: Record<ActionType, string> = {
  set_chief_complaint: 'Motivo de consulta',
  add_allergy: 'Alergia',
  add_medication: 'Medicamento',
  add_medical_history: 'Antecedente',
  add_vital_signs: 'Signos vitales',
  add_tooth_finding: 'Hallazgo del odontograma',
  add_planned_procedure: 'Procedimiento planificado',
  add_performed_procedure: 'Procedimiento realizado',
  add_diagnosis: 'Diagnostico',
  append_note: 'Nota clinica',
  schedule_followup: 'Cita de control',
}

export type Destination = 'Expediente' | 'Odontograma' | 'Diagnostico' | 'Plan de tratamiento' | 'Agenda'

export const ACTION_TYPE_DESTINATION: Record<ActionType, Destination> = {
  set_chief_complaint: 'Expediente',
  add_allergy: 'Expediente',
  add_medication: 'Expediente',
  add_medical_history: 'Expediente',
  add_vital_signs: 'Expediente',
  append_note: 'Expediente',
  add_tooth_finding: 'Odontograma',
  add_diagnosis: 'Diagnostico',
  add_planned_procedure: 'Plan de tratamiento',
  add_performed_procedure: 'Plan de tratamiento',
  schedule_followup: 'Agenda',
}

const NOTE_SECTION_LABELS: Record<string, string> = {
  S: 'Subjetivo',
  O: 'Objetivo',
  A: 'Analisis',
  P: 'Plan',
  free: 'Notas adicionales',
}

/** Resumen de una linea para la tarjeta de la propuesta -- distinto por tipo de accion. */
export function describeSuggestion(suggestion: AiSuggestionOut): string {
  const p = suggestion.payload
  switch (suggestion.action_type) {
    case 'set_chief_complaint':
      return String(p.text ?? '')
    case 'add_allergy':
      return `${p.substance ?? ''}${p.reaction ? ` — ${p.reaction}` : ''}`
    case 'add_medication':
      return `${p.name ?? ''}${p.dose ? ` — ${p.dose}` : ''}`
    case 'add_medical_history':
      return String(p.text ?? '')
    case 'add_vital_signs': {
      const parts: string[] = []
      if (p.bp_sys && p.bp_dia) parts.push(`${p.bp_sys}/${p.bp_dia} mmHg`)
      if (p.hr) parts.push(`${p.hr} lpm`)
      if (p.temp) parts.push(`${p.temp} °C`)
      return parts.join(' · ') || 'Sin valores'
    }
    case 'add_tooth_finding': {
      const code = p.finding_code as FindingCode | undefined
      const surfaces = Array.isArray(p.surfaces) ? (p.surfaces as string[]) : []
      const label = code ? FINDING_CATALOG[code]?.label ?? code : ''
      return `Pieza ${p.tooth_fdi ?? '?'}${surfaces.length ? ` (${surfaces.join(', ')})` : ''}: ${label}`
    }
    case 'add_planned_procedure':
    case 'add_performed_procedure': {
      const tooth = p.tooth_fdi ? `pieza ${p.tooth_fdi}` : 'sin pieza especifica'
      return `${p.procedure_code ?? ''} (${tooth})`
    }
    case 'add_diagnosis': {
      const code = p.diagnosis_code as DiagnosisCode | undefined
      const label = code ? DIAGNOSIS_CATALOG[code] : null
      return `${label ? `${label}: ` : ''}${p.text ?? ''}`
    }
    case 'append_note': {
      const section = NOTE_SECTION_LABELS[String(p.section)] ?? String(p.section)
      return `${section}: ${p.text ?? ''}`
    }
    case 'schedule_followup':
      return `En ${p.in_days ?? '?'} dias — ${p.reason ?? ''}`
    default:
      return JSON.stringify(p)
  }
}

/** Las acciones que afectan directamente al odontograma o al plan ameritan mostrar las
 * alertas criticas del paciente antes de aceptar (docs/03 sec. 8). */
export function needsAlertReview(actionType: ActionType): boolean {
  return (
    actionType === 'add_tooth_finding' ||
    actionType === 'add_planned_procedure' ||
    actionType === 'add_performed_procedure'
  )
}
