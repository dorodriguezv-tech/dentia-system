import type { SignerRelationship, TemplateCode } from './types'

/**
 * Copia minima, solo para la interfaz, del catalogo de
 * backend/app/modules/documents/rules.py (fuente de verdad real).
 */
export const TEMPLATE_CODE_LABELS: Record<TemplateCode, string> = {
  general: 'General',
  extraccion: 'Extraccion',
  endodoncia: 'Endodoncia',
  anestesia: 'Anestesia',
}

export const TEMPLATE_CODES = Object.keys(TEMPLATE_CODE_LABELS) as TemplateCode[]

export const SIGNER_RELATIONSHIP_LABELS: Record<SignerRelationship, string> = {
  paciente: 'Paciente',
  tutor: 'Tutor',
  otro: 'Otro',
}
