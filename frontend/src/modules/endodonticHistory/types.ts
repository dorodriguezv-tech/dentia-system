// Fase F (rediseno del expediente, docs/clinica): Historia Clinica de
// Endodoncia. Shapes exactos tomados de
// backend/app/modules/endodontic_history/schemas.py y rules.py -- no inventar
// campos, cualquier duda se resuelve leyendo esos archivos.

export type Origin = 'MANUAL' | 'AI_ASSISTED'

// --------------------------------------------------------------------------------
// 1. Interrogatorio + examen intrabucal/extrabucal.
// --------------------------------------------------------------------------------

export const ANTECEDENTES_KEYS = [
  'caries',
  'traumatismo',
  'abrasion',
  'resina',
  'amalgama',
  'incrustacion',
  'corona_poste',
  'tratamiento_conductos',
  'otros',
] as const
export type AntecedenteKey = (typeof ANTECEDENTES_KEYS)[number]
export const ANTECEDENTES_LABELS: Record<AntecedenteKey, string> = {
  caries: 'Caries',
  traumatismo: 'Traumatismo',
  abrasion: 'Abrasión',
  resina: 'Resina',
  amalgama: 'Amalgama',
  incrustacion: 'Incrustación',
  corona_poste: 'Corona/poste',
  tratamiento_conductos: 'Tratamiento de conductos',
  otros: 'Otros',
}

export const DOLOR_KEYS = ['localizado', 'irradiado', 'espontaneo', 'provocado', 'otro'] as const
export type DolorKey = (typeof DOLOR_KEYS)[number]
export const DOLOR_LABELS: Record<DolorKey, string> = {
  localizado: 'Localizado',
  irradiado: 'Irradiado',
  espontaneo: 'Espontáneo',
  provocado: 'Provocado',
  otro: 'Otro',
}

export const ESTIMULO_KEYS = ['frio', 'calor', 'masticacion', 'dulce', 'otro'] as const
export type EstimuloKey = (typeof ESTIMULO_KEYS)[number]
export const ESTIMULO_LABELS: Record<EstimuloKey, string> = {
  frio: 'Frío',
  calor: 'Calor',
  masticacion: 'Masticación',
  dulce: 'Dulce',
  otro: 'Otro',
}

export const EXAMEN_INTRABUCAL_KEYS = [
  'exposicion_pulpar',
  'inflamacion',
  'fistula',
  'traumatismo',
  'lesion_tejidos_blandos',
  'otro',
] as const
export type ExamenIntrabucalKey = (typeof EXAMEN_INTRABUCAL_KEYS)[number]
export const EXAMEN_INTRABUCAL_LABELS: Record<ExamenIntrabucalKey, string> = {
  exposicion_pulpar: 'Exposición pulpar',
  inflamacion: 'Inflamación',
  fistula: 'Fístula',
  traumatismo: 'Traumatismo',
  lesion_tejidos_blandos: 'Lesión de tejidos blandos',
  otro: 'Otro',
}

export const EXAMEN_EXTRABUCAL_KEYS = ['inflamacion', 'fistula', 'ganglios_linfaticos', 'otro'] as const
export type ExamenExtrabucalKey = (typeof EXAMEN_EXTRABUCAL_KEYS)[number]
export const EXAMEN_EXTRABUCAL_LABELS: Record<ExamenExtrabucalKey, string> = {
  inflamacion: 'Inflamación',
  fistula: 'Fístula',
  ganglios_linfaticos: 'Ganglios linfáticos',
  otro: 'Otro',
}

export interface EndodonticInterrogationOut {
  id: string
  encounter_id: string
  antecedentes: Record<string, boolean>
  antecedentes_otro_detalle: string | null
  dolor: Record<string, boolean>
  dolor_otro_detalle: string | null
  estimulo: Record<string, boolean>
  estimulo_otro_detalle: string | null
  examen_intrabucal: Record<string, boolean>
  examen_intrabucal_otro_detalle: string | null
  examen_extrabucal: Record<string, boolean>
  examen_extrabucal_otro_detalle: string | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface EndodonticInterrogationCreateInput {
  encounter_id: string
  antecedentes: Record<string, boolean>
  antecedentes_otro_detalle?: string | null
  dolor: Record<string, boolean>
  dolor_otro_detalle?: string | null
  estimulo: Record<string, boolean>
  estimulo_otro_detalle?: string | null
  examen_intrabucal: Record<string, boolean>
  examen_intrabucal_otro_detalle?: string | null
  examen_extrabucal: Record<string, boolean>
  examen_extrabucal_otro_detalle?: string | null
}

// --------------------------------------------------------------------------------
// 2. Pruebas de sensibilidad pulpar (lista repetible por encuentro).
// --------------------------------------------------------------------------------

export interface EndodonticPulpSensitivityTestOut {
  id: string
  encounter_id: string
  frio: boolean
  calor: boolean
  fugaz: boolean
  persistente: boolean
  localizado: boolean
  irradiado: boolean
  decrece: boolean
  incrementa: boolean
  diente_testigo_od: string | null
  prueba_cavidad: string | null
  prueba_electrica_od: string | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface EndodonticPulpSensitivityTestCreateInput {
  encounter_id: string
  frio: boolean
  calor: boolean
  fugaz: boolean
  persistente: boolean
  localizado: boolean
  irradiado: boolean
  decrece: boolean
  incrementa: boolean
  diente_testigo_od?: string | null
  prueba_cavidad?: string | null
  prueba_electrica_od?: string | null
}

// --------------------------------------------------------------------------------
// 3. Pruebas periodontales.
// --------------------------------------------------------------------------------

export const PERCUSION_KEYS = ['fugaz', 'persistente', 'localizado', 'irradiado'] as const
export type PercusionKey = (typeof PERCUSION_KEYS)[number]
export const PERCUSION_LABELS: Record<PercusionKey, string> = {
  fugaz: 'Fugaz',
  persistente: 'Persistente',
  localizado: 'Localizado',
  irradiado: 'Irradiado',
}

export type MovilidadValue = 'positiva' | 'negativa'
export const MOVILIDAD_LABELS: Record<MovilidadValue, string> = {
  positiva: 'Positiva',
  negativa: 'Negativa',
}
export type MovilidadGrado = 'I' | 'II' | 'III'
export type PalpacionValue = 'positiva' | 'negativa'

export interface EndodonticPeriodontalTestOut {
  id: string
  encounter_id: string
  percusion_horizontal: Record<string, boolean>
  movilidad_horizontal: MovilidadValue | null
  movilidad_horizontal_grado: MovilidadGrado | null
  percusion_vertical: Record<string, boolean>
  movilidad_vertical: MovilidadValue | null
  movilidad_vertical_grado: MovilidadGrado | null
  palpacion: PalpacionValue | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface EndodonticPeriodontalTestCreateInput {
  encounter_id: string
  percusion_horizontal: Record<string, boolean>
  movilidad_horizontal?: MovilidadValue | null
  movilidad_horizontal_grado?: MovilidadGrado | null
  percusion_vertical: Record<string, boolean>
  movilidad_vertical?: MovilidadValue | null
  movilidad_vertical_grado?: MovilidadGrado | null
  palpacion?: PalpacionValue | null
}

// --------------------------------------------------------------------------------
// 4. Interpretacion radiografica.
// --------------------------------------------------------------------------------

export const CAMARA_KEYS = [
  'normal',
  'estrecha',
  'calcificada',
  'fractura',
  'perforacion',
  'retraccion',
  'obstruccion',
  'otro',
] as const
export type CamaraKey = (typeof CAMARA_KEYS)[number]
export const CAMARA_LABELS: Record<CamaraKey, string> = {
  normal: 'Normal',
  estrecha: 'Estrecha',
  calcificada: 'Calcificada',
  fractura: 'Fractura',
  perforacion: 'Perforación',
  retraccion: 'Retracción',
  obstruccion: 'Obstrucción',
  otro: 'Otro',
}

export const CONDUCTO_KEYS = [
  'normal_estrecho',
  'amplio_preparado',
  'obturado',
  'inmaduro',
  'resorcion_interna',
  'perforado',
  'calcificado',
  'fractura',
  'otro',
] as const
export type ConductoKey = (typeof CONDUCTO_KEYS)[number]
export const CONDUCTO_LABELS: Record<ConductoKey, string> = {
  normal_estrecho: 'Normal/estrecho',
  amplio_preparado: 'Amplio/preparado',
  obturado: 'Obturado',
  inmaduro: 'Inmaduro',
  resorcion_interna: 'Resorción interna',
  perforado: 'Perforado',
  calcificado: 'Calcificado',
  fractura: 'Fractura',
  otro: 'Otro',
}

export const PERIODONTO_KEYS = [
  'normal_ensanchado',
  'resorcion_apical',
  'hipercementosis',
  'lesion_difusa',
  'lesion_circunscrita',
  'otro',
] as const
export type PeriodontoKey = (typeof PERIODONTO_KEYS)[number]
export const PERIODONTO_LABELS: Record<PeriodontoKey, string> = {
  normal_ensanchado: 'Normal/ensanchado',
  resorcion_apical: 'Resorción apical',
  hipercementosis: 'Hipercementosis',
  lesion_difusa: 'Lesión difusa',
  lesion_circunscrita: 'Lesión circunscrita',
  otro: 'Otro',
}

export interface EndodonticRadiographicInterpretationOut {
  id: string
  encounter_id: string
  camara: Record<string, boolean>
  camara_otro_detalle: string | null
  conducto: Record<string, boolean>
  conducto_otro_detalle: string | null
  periodonto: Record<string, boolean>
  periodonto_otro_detalle: string | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface EndodonticRadiographicInterpretationCreateInput {
  encounter_id: string
  camara: Record<string, boolean>
  camara_otro_detalle?: string | null
  conducto: Record<string, boolean>
  conducto_otro_detalle?: string | null
  periodonto: Record<string, boolean>
  periodonto_otro_detalle?: string | null
}

// --------------------------------------------------------------------------------
// 5. Diagnostico y tratamiento.
// --------------------------------------------------------------------------------

export type DiagnosticoPulpar =
  | 'pulpa_sana'
  | 'pulpitis_reversible'
  | 'pulpitis_irreversible'
  | 'necrosis_pulpar'
  | 'despulpado'
  | 'pulpitis_hiperplasica'
export const DIAGNOSTICO_PULPAR_LABELS: Record<DiagnosticoPulpar, string> = {
  pulpa_sana: 'Pulpa sana',
  pulpitis_reversible: 'Pulpitis reversible',
  pulpitis_irreversible: 'Pulpitis irreversible',
  necrosis_pulpar: 'Necrosis pulpar',
  despulpado: 'Despulpado',
  pulpitis_hiperplasica: 'Pulpitis hiperplásica',
}

export type DiagnosticoPeriapical =
  | 'periapice_sano'
  | 'periodontitis_aguda'
  | 'periodontitis_cronica'
  | 'osteitis_condensante'
  | 'absceso_alveolar_agudo'
  | 'absceso_fenix_cronico'
export const DIAGNOSTICO_PERIAPICAL_LABELS: Record<DiagnosticoPeriapical, string> = {
  periapice_sano: 'Periápice sano',
  periodontitis_aguda: 'Periodontitis aguda',
  periodontitis_cronica: 'Periodontitis crónica',
  osteitis_condensante: 'Osteítis condensante',
  absceso_alveolar_agudo: 'Absceso alveolar agudo',
  absceso_fenix_cronico: 'Absceso fénix crónico',
}

export const TRATAMIENTO_KEYS = [
  'biopulpectomia',
  'necropulpectomia',
  'repeticion_tratamiento',
  'extirpacion_intencional',
  'apicoformacion',
  'recromia',
  'perno_munon',
] as const
export type TratamientoKey = (typeof TRATAMIENTO_KEYS)[number]
export const TRATAMIENTO_LABELS: Record<TratamientoKey, string> = {
  biopulpectomia: 'Biopulpectomía',
  necropulpectomia: 'Necropulpectomía',
  repeticion_tratamiento: 'Repetición de tratamiento',
  extirpacion_intencional: 'Extirpación intencional',
  apicoformacion: 'Apicoformación',
  recromia: 'Recromía',
  perno_munon: 'Perno muñón',
}

export const CIRUGIA_KEYS = [
  'curetaje_apical',
  'apicectomia',
  'radisectomia',
  'hemiseccion',
  'amputacion_radicular',
] as const
export type CirugiaKey = (typeof CIRUGIA_KEYS)[number]
export const CIRUGIA_LABELS: Record<CirugiaKey, string> = {
  curetaje_apical: 'Curetaje apical',
  apicectomia: 'Apicectomía',
  radisectomia: 'Radisección',
  hemiseccion: 'Hemisección',
  amputacion_radicular: 'Amputación radicular',
}

export interface EndodonticDiagnosisTreatmentOut {
  id: string
  encounter_id: string
  diagnostico_pulpar: DiagnosticoPulpar | null
  diagnostico_periapical: DiagnosticoPeriapical | null
  tratamiento: Record<string, boolean>
  cirugia: Record<string, boolean>
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface EndodonticDiagnosisTreatmentCreateInput {
  encounter_id: string
  diagnostico_pulpar?: DiagnosticoPulpar | null
  diagnostico_periapical?: DiagnosticoPeriapical | null
  tratamiento: Record<string, boolean>
  cirugia: Record<string, boolean>
}

// --------------------------------------------------------------------------------
// 6. Odontograma de diagnostico/evolucion -- 18 codigos por pieza.
// --------------------------------------------------------------------------------

export type EndodonticToothKind = 'diagnostico' | 'evolucion'

// Copiado literal de backend/app/modules/endodontic_history/rules.py::ENDODONTIC_TOOTH_CODES
export const ENDODONTIC_TOOTH_CODES: readonly [number, string][] = [
  [0, 'Sano'],
  [1, 'Con caries'],
  [2, 'Obturado con caries'],
  [3, 'Obturado sin caries'],
  [4, 'Perdido por caries'],
  [5, 'Perdido por otro motivo'],
  [6, 'Fisura obturada'],
  [7, 'Soporte de puente, corona, funda o implante'],
  [8, 'Diente sin erupcionar'],
  [9, 'Traumatismo/fractura'],
  [10, 'No registrado'],
  [11, 'Recesión gingival'],
  [12, 'Tratamiento de conductos'],
  [13, 'Instrumento separado en conducto'],
  [14, 'Bolsas periodontales'],
  [15, 'Fluorosis'],
  [16, 'Alteraciones de forma/número/tamaño/textura/posición'],
  [17, 'Lesión endoperiodontal'],
]
export const ENDODONTIC_TOOTH_CODE_LABELS: Record<number, string> = Object.fromEntries(
  ENDODONTIC_TOOTH_CODES,
)

export interface EndodonticToothDiagnosisCodeOut {
  id: string
  encounter_id: string
  tooth_fdi: string
  kind: EndodonticToothKind
  code: number
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface EndodonticToothDiagnosisCodeCreateInput {
  encounter_id: string
  tooth_fdi: string
  kind: EndodonticToothKind
  code: number
}

// --------------------------------------------------------------------------------
// 7. Longitud de trabajo + datos de tratamiento.
// --------------------------------------------------------------------------------

export const CANAL_KEYS = [
  'mesial',
  'mesiolingual',
  'mesiovestibular',
  'mesiopalatino',
  'distal',
  'distolingual',
  'distopalatino',
  'distovestibular',
  'palatino',
  'unico',
] as const
export type CanalKey = (typeof CANAL_KEYS)[number]
export const CANAL_LABELS: Record<CanalKey, string> = {
  mesial: 'Mesial',
  mesiolingual: 'Mesiolingual',
  mesiovestibular: 'Mesiovestibular',
  mesiopalatino: 'Mesiopalatino',
  distal: 'Distal',
  distolingual: 'Distolingual',
  distopalatino: 'Distopalatino',
  distovestibular: 'Distovestibular',
  palatino: 'Palatino',
  unico: 'Único',
}

export interface CanalMeasurementDetail {
  aparente_rx?: string | null
  real_localizador?: string | null
  relacion?: string | null
}

export interface EndodonticWorkingLengthOut {
  id: string
  encounter_id: string
  tooth_fdi: string | null
  canal_measurements: Record<string, CanalMeasurementDetail>
  tecnica_instrumentacion: string | null
  tecnica_obturacion: string | null
  indicaciones: string | null
  fecha_inicio: string | null
  fecha_termino: string | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface EndodonticWorkingLengthCreateInput {
  encounter_id: string
  tooth_fdi?: string | null
  canal_measurements: Record<string, CanalMeasurementDetail>
  tecnica_instrumentacion?: string | null
  tecnica_obturacion?: string | null
  indicaciones?: string | null
  fecha_inicio?: string | null
  fecha_termino?: string | null
}
