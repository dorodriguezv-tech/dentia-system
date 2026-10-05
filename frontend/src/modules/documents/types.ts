export type TemplateCode = 'general' | 'extraccion' | 'endodoncia' | 'anestesia'
export type SignerRelationship = 'paciente' | 'tutor' | 'otro'

export interface DocumentTemplateOut {
  id: string
  code: TemplateCode
  name: string
  version: number
  html_content: string
  is_current: boolean
  created_at: string
}

export interface DocumentTemplateCreateInput {
  code: TemplateCode
  name: string
  html_content: string
}

export interface ConsentOut {
  id: string
  patient_id: string
  encounter_id: string
  template_id: string
  procedure_planned_id: string | null
  treatment_plan_id: string | null
  professional_id: string
  signer_name: string
  signer_relationship: SignerRelationship
  content_hash: string
  signed_at: string
  is_active: boolean
  annul_reason: string | null
}

export interface ConsentCreateInput {
  encounter_id: string
  template_code: TemplateCode
  treatment_plan_id?: string | null
  signer_name: string
  signer_relationship: SignerRelationship
  signature_png_base64: string
}
