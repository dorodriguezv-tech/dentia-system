// 24 formatos oficiales reales de docs/formatos (ver plan aprobado) --
// fuente de verdad: backend/app/modules/documents/schemas.py::TemplateCode.
export type TemplateCode =
  | 'protesis_fija'
  | 'aplicacion_fluor'
  | 'anestesia_local_oral'
  | 'exodoncia'
  | 'incrustacion_dental'
  | 'obturacion_dental'
  | 'endodoncia'
  | 'protesis_removible'
  | 'sellado_fosetas_fisuras'
  | 'toma_radiografias'
  | 'limpieza_dental'
  | 'aplicacion_fluor_pediatrico'
  | 'anestesia_local_pediatrico'
  | 'corona_metalica_pediatrico'
  | 'sellado_fosetas_pediatrico'
  | 'obturacion_resina_pediatrico'
  | 'profilaxis_pediatrico'
  | 'toma_radiografias_pediatrico'
  | 'tratamiento_pulpar_pediatrico'
  | 'aviso_privacidad'
  | 'carta_tratamiento_concluido'
  | 'carta_tratamiento_suspendido'
  | 'carta_autorizacion_uso_imagen'
  | 'carta_caso_medico_legal'

export type TemplateCategory = 'consentimiento' | 'aviso_privacidad' | 'carta'

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
  extra_fields: Record<string, string> | null
  witness1_name: string | null
  witness2_name: string | null
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
  extra_fields?: Record<string, string>
  witness1_name?: string | null
  witness2_name?: string | null
}

// Lo que el paso 2 del formulario de firma necesita para mostrar "datos que
// se usaran" + "falta completar" (ver documents/service.py::build_consent_prefill
// en el backend -- fuente de verdad real, esto solo tipa la respuesta).
export interface ExtraFieldPrefill {
  label: string
  required: boolean
  multiline: boolean
  value: string | null
}

export interface ConsentPrefillOut {
  variables: Record<string, unknown>
  extra_fields: Record<string, ExtraFieldPrefill>
}

// --------------------------------------------------------------------------------
// Fase D (docs/clinica, "Documentos imprimibles nuevos"): receta, hoja de
// referencia/interconsulta y hoja de contrarreferencia. Shapes exactos tomados de
// backend/app/modules/clinical_documents/schemas.py -- no inventar campos, cualquier
// duda se resuelve leyendo ese archivo. A diferencia de Consent, estos documentos no
// llevan firma digital (se firman a mano al imprimir).
// --------------------------------------------------------------------------------

export interface PrescriptionMedicationItem {
  nombre: string
  detalle: string
}

export interface PrescriptionOut {
  id: string
  patient_id: string
  encounter_id: string
  folio: string
  diagnostico: string
  medications: PrescriptionMedicationItem[]
  is_active: boolean
  annul_reason: string | null
  created_at: string
}

export interface PrescriptionCreateInput {
  encounter_id: string
  diagnostico: string
  medications: PrescriptionMedicationItem[]
}

export interface ReferralNoteOut {
  id: string
  patient_id: string
  encounter_id: string
  diagnosticos: string | null
  medicamentos_texto: string | null
  alergias_texto: string | null
  tratamientos_texto: string | null
  observaciones: string | null
  motivo_interconsulta: string
  establecimiento_receptor: string
  is_active: boolean
  annul_reason: string | null
  created_at: string
}

export interface ReferralNoteCreateInput {
  encounter_id: string
  diagnosticos?: string | null
  medicamentos_texto?: string | null
  alergias_texto?: string | null
  tratamientos_texto?: string | null
  observaciones?: string | null
  motivo_interconsulta: string
  establecimiento_receptor: string
}

export interface CounterReferralNoteOut {
  id: string
  patient_id: string
  encounter_id: string
  referral_note_id: string | null
  motivo_contrarreferencia: string
  tratamientos_texto: string | null
  observaciones: string | null
  motivo_interconsulta_original: string | null
  establecimiento_emisor: string
  is_active: boolean
  annul_reason: string | null
  created_at: string
}

export interface CounterReferralNoteCreateInput {
  encounter_id: string
  referral_note_id?: string | null
  motivo_contrarreferencia: string
  tratamientos_texto?: string | null
  observaciones?: string | null
  motivo_interconsulta_original?: string | null
  establecimiento_emisor: string
}
