// Fase C (rediseno del expediente, docs/clinica): Historia Clinica Odontologica.
// Shapes exactos tomados de backend/app/modules/odontological_history/schemas.py
// y rules.py -- no inventar campos, cualquier duda se resuelve leyendo esos
// archivos.

export type Origin = 'MANUAL' | 'AI_ASSISTED'

// --------------------------------------------------------------------------------
// 1. Exploracion cabeza/cuello + biotipo facial + ATM + tejidos blandos.
// --------------------------------------------------------------------------------

export interface OdontologicalExamOut {
  id: string
  encounter_id: string
  skull_type: string | null
  facial_biotype: string | null
  facial_biotype_observations: string | null
  apertura_conservada_mm: number | null
  apertura_limitada_mm: number | null
  chasquidos_derecho: boolean
  crepitacion_derecho: boolean
  chasquidos_izquierdo: boolean
  crepitacion_izquierdo: boolean
  dolor_apertura_lateralidad: boolean
  fatiga_dolor_muscular: boolean
  desviacion_apertura_cierre: boolean
  atm_observaciones: string | null
  ganglios: string | null
  carrillos: string | null
  labios: string | null
  lengua: string | null
  piso_boca: string | null
  region_retromolar: string | null
  paladar_duro_blando: string | null
  faringe: string | null
  encia_libre_marginal: string | null
  tejidos_blandos_observaciones: string | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface OdontologicalExamCreateInput {
  encounter_id: string
  skull_type?: string | null
  facial_biotype?: string | null
  facial_biotype_observations?: string | null
  apertura_conservada_mm?: number | null
  apertura_limitada_mm?: number | null
  chasquidos_derecho: boolean
  crepitacion_derecho: boolean
  chasquidos_izquierdo: boolean
  crepitacion_izquierdo: boolean
  dolor_apertura_lateralidad: boolean
  fatiga_dolor_muscular: boolean
  desviacion_apertura_cierre: boolean
  atm_observaciones?: string | null
  ganglios?: string | null
  carrillos?: string | null
  labios?: string | null
  lengua?: string | null
  piso_boca?: string | null
  region_retromolar?: string | null
  paladar_duro_blando?: string | null
  faringe?: string | null
  encia_libre_marginal?: string | null
  tejidos_blandos_observaciones?: string | null
}

// --------------------------------------------------------------------------------
// 2. Anamnesis periodontal.
// --------------------------------------------------------------------------------

export type PeriodontalAnswer = 'si' | 'no' | 'no_recuerda'
export const PERIODONTAL_ANSWER_LABELS: Record<PeriodontalAnswer, string> = {
  si: 'Sí',
  no: 'No',
  no_recuerda: 'No recuerda',
}

export type OralHealthSelfPerception = 'buena' | 'regular' | 'mala'
export const ORAL_HEALTH_SELF_PERCEPTION_LABELS: Record<OralHealthSelfPerception, string> = {
  buena: 'Buena',
  regular: 'Regular',
  mala: 'Mala',
}

export interface PeriodontalAnamnesisOut {
  id: string
  encounter_id: string
  answers: Record<string, string>
  cepillado_veces_dia: number | null
  cepillado_pasta: string | null
  insatisfaccion_motivo: string | null
  tratamiento_medico_detalle: string | null
  medicamento_actual: string | null
  cirugia_detalle: string | null
  hormonas_para_que: string | null
  habito_danino_cual: string | null
  fuma_cigarros_dia: number | null
  alcohol_veces_semana: number | null
  ultimo_examen_odontologico: string | null
  salud_bucal_autopercibida: OralHealthSelfPerception | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface PeriodontalAnamnesisCreateInput {
  encounter_id: string
  answers: Record<string, PeriodontalAnswer>
  cepillado_veces_dia?: number | null
  cepillado_pasta?: string | null
  insatisfaccion_motivo?: string | null
  tratamiento_medico_detalle?: string | null
  medicamento_actual?: string | null
  cirugia_detalle?: string | null
  hormonas_para_que?: string | null
  habito_danino_cual?: string | null
  fuma_cigarros_dia?: number | null
  alcohol_veces_semana?: number | null
  ultimo_examen_odontologico?: string | null
  salud_bucal_autopercibida?: OralHealthSelfPerception | null
}

// --------------------------------------------------------------------------------
// 3. Auxiliares de diagnostico -- analisis radiografico.
// --------------------------------------------------------------------------------

export const RADIOGRAPHIC_FINDING_TYPES = [
  'perdida_osea_horizontal',
  'perdida_osea_vertical',
  'alteraciones_forma_longitud_radicular',
  'ensanchamiento_ligamento_periodontal',
  'hallazgos',
] as const

export type RadiographicFindingType = (typeof RADIOGRAPHIC_FINDING_TYPES)[number]

export const RADIOGRAPHIC_FINDING_LABELS: Record<RadiographicFindingType, string> = {
  perdida_osea_horizontal: 'Pérdida ósea horizontal',
  perdida_osea_vertical: 'Pérdida ósea vertical',
  alteraciones_forma_longitud_radicular: 'Alteraciones de forma/longitud radicular',
  ensanchamiento_ligamento_periodontal: 'Ensanchamiento del ligamento periodontal',
  hallazgos: 'Otros hallazgos',
}

export interface RadiographicFindingDetail {
  organos_dentarios: string
  porcentaje?: string | null
  alteracion?: string | null
}

export interface RadiographicAnalysisOut {
  id: string
  encounter_id: string
  findings: Partial<Record<RadiographicFindingType, RadiographicFindingDetail>>
  anexos_nota: string | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface RadiographicAnalysisCreateInput {
  encounter_id: string
  findings: Partial<Record<RadiographicFindingType, RadiographicFindingDetail>>
  anexos_nota?: string | null
}

// --------------------------------------------------------------------------------
// 4. Odontograma de diagnostico -- datos complementarios.
// --------------------------------------------------------------------------------

export type KennedyClass = 'I' | 'II' | 'III'
export const KENNEDY_CLASS_LABELS: Record<KennedyClass, string> = {
  I: 'Clase I',
  II: 'Clase II',
  III: 'Clase III',
}

export interface FixedProsthesisEntry {
  tooth_fdi: string
  cr_relation: string
}

export interface OdontogramDiagnosisDetailOut {
  id: string
  encounter_id: string
  edentulous_space_available: boolean | null
  edentulous_space_comments: string | null
  kennedy_sup_class: KennedyClass | null
  kennedy_sup_modification: boolean
  kennedy_inf_class: KennedyClass | null
  kennedy_inf_modification: boolean
  fixed_prosthesis_analysis: FixedProsthesisEntry[]
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface OdontogramDiagnosisDetailCreateInput {
  encounter_id: string
  edentulous_space_available?: boolean | null
  edentulous_space_comments?: string | null
  kennedy_sup_class?: KennedyClass | null
  kennedy_sup_modification: boolean
  kennedy_inf_class?: KennedyClass | null
  kennedy_inf_modification: boolean
  fixed_prosthesis_analysis: FixedProsthesisEntry[]
}

// --------------------------------------------------------------------------------
// 5. Analisis con paralelometro.
// --------------------------------------------------------------------------------

export interface ParallelometerEntry {
  organo_dental: string
  caracteristicas: string
  plan_tratamiento: string
}

export interface ParallelometerAnalysisOut {
  id: string
  encounter_id: string
  entries: ParallelometerEntry[]
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface ParallelometerAnalysisCreateInput {
  encounter_id: string
  entries: ParallelometerEntry[]
}

// --------------------------------------------------------------------------------
// 6. Diseno de protesis parcial removible.
// --------------------------------------------------------------------------------

export interface RemovablePartialDentureDesignOut {
  id: string
  encounter_id: string
  conector_mayor: string | null
  conector_menor: string | null
  retenedores_directos: string | null
  conectores_indirectos: string | null
  base_protesica: string | null
  dientes_artificiales: string | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface RemovablePartialDentureDesignCreateInput {
  encounter_id: string
  conector_mayor?: string | null
  conector_menor?: string | null
  retenedores_directos?: string | null
  conectores_indirectos?: string | null
  base_protesica?: string | null
  dientes_artificiales?: string | null
}

// --------------------------------------------------------------------------------
// 7/8. Diagnostico y plan de tratamiento por organo dental.
// --------------------------------------------------------------------------------

export interface ToothDiagnosisEntryOut {
  id: string
  encounter_id: string
  diagnoses: Record<string, string>
  observaciones: string | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface ToothDiagnosisEntryCreateInput {
  encounter_id: string
  diagnoses: Record<string, string>
  observaciones?: string | null
}

export interface ToothTreatmentPlanEntryOut {
  id: string
  encounter_id: string
  plans: Record<string, string>
  observaciones: string | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface ToothTreatmentPlanEntryCreateInput {
  encounter_id: string
  plans: Record<string, string>
  observaciones?: string | null
}
