// Fase G (rediseno del expediente, docs/clinica -- ULTIMO slice del
// proyecto): Periodontograma completo. Shapes exactos tomados de
// backend/app/modules/periodontogram/schemas.py y rules.py -- no inventar
// campos, cualquier duda se resuelve leyendo esos archivos.

export type Origin = 'MANUAL' | 'AI_ASSISTED'

// --------------------------------------------------------------------------------
// 1. Sondeo periodontal -- 6 sitios estandar por pieza.
// --------------------------------------------------------------------------------

export type ProbingSite =
  | 'mesiovestibular'
  | 'vestibular'
  | 'distovestibular'
  | 'mesiolingual'
  | 'lingual'
  | 'distolingual'

// Mismo orden que rules.PROBING_SITES. "lingual"/"mesiolingual"/
// "distolingual" ya llevan la etiqueta combinada "Lingual/Palatino" (y
// variantes) tal cual la define el backend -- es la unica fuente de verdad
// para el texto de interfaz, no se reinterpreta por arcada en el frontend.
export const PROBING_SITES: ProbingSite[] = [
  'mesiovestibular',
  'vestibular',
  'distovestibular',
  'mesiolingual',
  'lingual',
  'distolingual',
]

export const PROBING_SITE_LABELS: Record<ProbingSite, string> = {
  mesiovestibular: 'Mesiovestibular',
  vestibular: 'Vestibular',
  distovestibular: 'Distovestibular',
  mesiolingual: 'Mesiolingual/Mesiopalatino',
  lingual: 'Lingual/Palatino',
  distolingual: 'Distolingual/Distopalatino',
}

// Agrupacion por cara, solo para la UI (la tabla de sondeo se divide en 2
// bloques de 3 sitios cada uno).
export const VESTIBULAR_FACE_SITES: ProbingSite[] = ['mesiovestibular', 'vestibular', 'distovestibular']
export const LINGUAL_FACE_SITES: ProbingSite[] = ['mesiolingual', 'lingual', 'distolingual']

export const PROBING_DEPTH_MM_MIN = 0
export const PROBING_DEPTH_MM_MAX = 15
export const RECESSION_MM_MIN = -5
export const RECESSION_MM_MAX = 15

export interface PeriodontalProbingSiteOut {
  id: string
  encounter_id: string
  tooth_fdi: string
  site: ProbingSite
  probing_depth_mm: number
  recession_mm: number
  bleeding_on_probing: boolean
  suppuration: boolean
  /** Calculado al vuelo por el backend (nunca persistido): NIC = profundidad + recesion. */
  clinical_attachment_level_mm: number | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface PeriodontalProbingSiteCreateInput {
  encounter_id: string
  tooth_fdi: string
  site: ProbingSite
  probing_depth_mm: number
  recession_mm: number
  bleeding_on_probing: boolean
  suppuration: boolean
}

// --------------------------------------------------------------------------------
// 2. Medicion por pieza -- movilidad (Miller) y furcacion.
// --------------------------------------------------------------------------------

export const MOBILITY_GRADE_MIN = 0
export const MOBILITY_GRADE_MAX = 3
export const FURCATION_GRADE_MIN = 0
export const FURCATION_GRADE_MAX = 3

export interface PeriodontalToothMeasurementOut {
  id: string
  encounter_id: string
  tooth_fdi: string
  mobility_grade: number | null
  furcation_grade: number | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface PeriodontalToothMeasurementCreateInput {
  encounter_id: string
  tooth_fdi: string
  mobility_grade: number | null
  furcation_grade: number | null
}

// --------------------------------------------------------------------------------
// 3. Indices de placa dentobacteriana y gingival.
// --------------------------------------------------------------------------------

export type IndexType = 'placa' | 'gingival'
export type IndexSurface = 'vestibular' | 'lingual'

export const INDEX_SURFACES: IndexSurface[] = ['vestibular', 'lingual']
export const INDEX_SURFACE_LABELS: Record<IndexSurface, string> = {
  vestibular: 'Vestibular',
  lingual: 'Lingual/Palatino',
}

export const INDEX_GRADE_MIN = 0
export const INDEX_GRADE_MAX = 3

// Texto literal de rules.py (PLAQUE_GRADE_LABELS/GINGIVAL_GRADE_LABELS, con
// acentos de es-MX) -- unica fuente de verdad, no se reformula.
export const PLAQUE_GRADE_LABELS: Record<number, string> = {
  0: 'Ausencia de placa',
  1: 'Placa en 1/3 de la superficie',
  2: 'Placa en 2/3 de la superficie',
  3: 'Placa en más de 2/3 de la superficie',
}

export const GINGIVAL_GRADE_LABELS: Record<number, string> = {
  0: 'Normal (encía sana)',
  1: 'Leve (cambio de color/edema leve, sin sangrado al sondaje)',
  2: 'Moderada (enrojecimiento evidente, sangrado al sondaje)',
  3: 'Severa (enrojecimiento/edema severo, ulceración, tendencia a sangrado espontáneo)',
}

export interface PeriodontalIndexEntryOut {
  id: string
  encounter_id: string
  tooth_fdi: string
  index_type: IndexType
  surface: IndexSurface
  grade: number
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface PeriodontalIndexEntryCreateInput {
  encounter_id: string
  tooth_fdi: string
  index_type: IndexType
  surface: IndexSurface
  grade: number
}

export interface PlaqueIndexSummary {
  numero_caras_totales: number
  numero_caras_pigmentadas: number
  indice_placa_dentobacteriana: number | null
}

export interface GingivalIndexSummary {
  numero_sitios_totales: number
  indice_gingival_total: number | null
}

export interface IndicesSummaryOut {
  encounter_id: string | null
  placa: PlaqueIndexSummary
  gingival: GingivalIndexSummary
}

// --------------------------------------------------------------------------------
// 4. Tablas de oclusion -- contactos marcados.
// --------------------------------------------------------------------------------

export type OcclusalMovement =
  | 'centrica'
  | 'lateralidad_izquierda'
  | 'protrusion'
  | 'lateralidad_derecha'

export const OCCLUSAL_MOVEMENTS: OcclusalMovement[] = [
  'centrica',
  'lateralidad_izquierda',
  'protrusion',
  'lateralidad_derecha',
]

export const OCCLUSAL_MOVEMENT_LABELS: Record<OcclusalMovement, string> = {
  centrica: 'Oclusión céntrica',
  lateralidad_izquierda: 'Lateralidad izquierda',
  protrusion: 'Protrusión',
  lateralidad_derecha: 'Lateralidad derecha',
}

export interface OcclusalContactEntryOut {
  id: string
  encounter_id: string
  tooth_fdi: string
  movement: OcclusalMovement
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface OcclusalContactEntryCreateInput {
  encounter_id: string
  tooth_fdi: string
  movement: OcclusalMovement
}

// --------------------------------------------------------------------------------
// 5. Observaciones del periodontograma.
// --------------------------------------------------------------------------------

export interface PeriodontogramObservationOut {
  id: string
  encounter_id: string
  observaciones: string | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface PeriodontogramObservationCreateInput {
  encounter_id: string
  observaciones: string | null
}
