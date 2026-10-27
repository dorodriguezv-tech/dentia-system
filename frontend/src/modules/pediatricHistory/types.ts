// Fase E (rediseno del expediente, docs/clinica): Historia Clinica Pediatrica.
// Shapes exactos tomados de backend/app/modules/pediatric_history/schemas.py y
// rules.py -- no inventar campos, cualquier duda se resuelve leyendo esos
// archivos.

export type Origin = 'MANUAL' | 'AI_ASSISTED'

// --------------------------------------------------------------------------------
// 1. Antecedentes perinatales y primer ano de vida.
// --------------------------------------------------------------------------------

export interface PediatricPerinatalHistoryOut {
  id: string
  encounter_id: string
  problemas_embarazo_perinatales: string | null
  tomo_medicamentos_embarazo: boolean | null
  tomo_medicamentos_embarazo_cuales: string | null
  embarazo_observaciones: string | null
  tomo_medicamentos_primer_ano: boolean | null
  tomo_medicamentos_primer_ano_cuales: string | null
  vacunas_completas: boolean | null
  fecha_ultima_visita_dentista: string | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface PediatricPerinatalHistoryCreateInput {
  encounter_id: string
  problemas_embarazo_perinatales?: string | null
  tomo_medicamentos_embarazo?: boolean | null
  tomo_medicamentos_embarazo_cuales?: string | null
  embarazo_observaciones?: string | null
  tomo_medicamentos_primer_ano?: boolean | null
  tomo_medicamentos_primer_ano_cuales?: string | null
  vacunas_completas?: boolean | null
  fecha_ultima_visita_dentista?: string | null
}

// --------------------------------------------------------------------------------
// 2. Habitos y antecedentes bucales.
// --------------------------------------------------------------------------------

export interface PediatricOralHabitsOut {
  id: string
  encounter_id: string
  cepilla_despues_alimento: boolean | null
  sangran_encias_sin_cepillar: boolean | null
  sabe_que_es_fluor: boolean | null
  fluoruro_sistematico_aplicado: boolean | null
  diente_extraido: boolean | null
  accidentes_fracturas_dentales: boolean | null
  dolor_dental_reciente: boolean | null
  bruxismo_nocturno: boolean | null
  respira_boca_frecuente: boolean | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface PediatricOralHabitsCreateInput {
  encounter_id: string
  cepilla_despues_alimento?: boolean | null
  sangran_encias_sin_cepillar?: boolean | null
  sabe_que_es_fluor?: boolean | null
  fluoruro_sistematico_aplicado?: boolean | null
  diente_extraido?: boolean | null
  accidentes_fracturas_dentales?: boolean | null
  dolor_dental_reciente?: boolean | null
  bruxismo_nocturno?: boolean | null
  respira_boca_frecuente?: boolean | null
}

export type PediatricOralHabitsField = Exclude<keyof PediatricOralHabitsCreateInput, 'encounter_id'>

export const ORAL_HABITS_FIELDS: { key: PediatricOralHabitsField; label: string }[] = [
  { key: 'cepilla_despues_alimento', label: 'Se cepilla despues de cada alimento' },
  { key: 'sangran_encias_sin_cepillar', label: 'Le sangran las encias sin cepillarse' },
  { key: 'sabe_que_es_fluor', label: 'Sabe que es el fluor' },
  { key: 'fluoruro_sistematico_aplicado', label: 'Se le ha aplicado fluoruro sistematico' },
  { key: 'diente_extraido', label: 'Le han extraido algun diente' },
  { key: 'accidentes_fracturas_dentales', label: 'Ha tenido accidentes o fracturas dentales' },
  { key: 'dolor_dental_reciente', label: 'Ha tenido dolor dental reciente' },
  { key: 'bruxismo_nocturno', label: 'Bruxismo nocturno (rechina los dientes)' },
  { key: 'respira_boca_frecuente', label: 'Respira por la boca con frecuencia' },
]

// --------------------------------------------------------------------------------
// 3. Madurez y conducta.
// --------------------------------------------------------------------------------

export interface PediatricBehaviorMaturityOut {
  id: string
  encounter_id: string
  experiencia_desfavorable_dentista: boolean | null
  se_relaciona_medico: boolean | null
  controla_esfinteres: boolean | null
  toma_biberon_actualmente: boolean | null
  edad_dejo_biberon: string | null
  succion_labio_dedo: boolean | null
  muerde_objetos_unas: boolean | null
  relacion_otros_ninos: string | null
  caracter: string | null
  observaciones: string | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface PediatricBehaviorMaturityCreateInput {
  encounter_id: string
  experiencia_desfavorable_dentista?: boolean | null
  se_relaciona_medico?: boolean | null
  controla_esfinteres?: boolean | null
  toma_biberon_actualmente?: boolean | null
  edad_dejo_biberon?: string | null
  succion_labio_dedo?: boolean | null
  muerde_objetos_unas?: boolean | null
  relacion_otros_ninos?: string | null
  caracter?: string | null
  observaciones?: string | null
}

export type PediatricBehaviorMaturityBooleanField =
  | 'experiencia_desfavorable_dentista'
  | 'se_relaciona_medico'
  | 'controla_esfinteres'
  | 'toma_biberon_actualmente'
  | 'succion_labio_dedo'
  | 'muerde_objetos_unas'

export const BEHAVIOR_BOOLEAN_FIELDS: {
  key: PediatricBehaviorMaturityBooleanField
  label: string
}[] = [
  { key: 'experiencia_desfavorable_dentista', label: 'Experiencia desfavorable con el dentista' },
  { key: 'se_relaciona_medico', label: 'Se relaciona bien con el personal medico' },
  { key: 'controla_esfinteres', label: 'Controla esfinteres' },
  { key: 'toma_biberon_actualmente', label: 'Toma biberon actualmente' },
  { key: 'succion_labio_dedo', label: 'Succion de labio o dedo' },
  { key: 'muerde_objetos_unas', label: 'Muerde objetos o se muerde las unas' },
]

// --------------------------------------------------------------------------------
// 4. Oclusion y alineamiento.
// --------------------------------------------------------------------------------

export type LineaMedia = 'normal' | 'desviada_izquierda' | 'desviada_derecha'
export const LINEA_MEDIA_LABELS: Record<LineaMedia, string> = {
  normal: 'Normal',
  desviada_izquierda: 'Desviada a la izquierda',
  desviada_derecha: 'Desviada a la derecha',
}

export type ClasificacionAngle = 'I' | 'II' | 'III'

export interface PediatricOcclusionOut {
  id: string
  encounter_id: string
  planos_terminales_izq: string | null
  planos_terminales_der: string | null
  angle_molar_izq: string | null
  angle_molar_der: string | null
  overjet_mm: number | null
  overbite_mm: number | null
  mordida_cruzada: boolean | null
  diastema: boolean | null
  mordida_abierta_ante_mm: number | null
  mordida_abierta_post_mm: number | null
  linea_media: LineaMedia | null
  clasificacion_angle: ClasificacionAngle | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface PediatricOcclusionCreateInput {
  encounter_id: string
  planos_terminales_izq?: string | null
  planos_terminales_der?: string | null
  angle_molar_izq?: string | null
  angle_molar_der?: string | null
  overjet_mm?: number | null
  overbite_mm?: number | null
  mordida_cruzada?: boolean | null
  diastema?: boolean | null
  mordida_abierta_ante_mm?: number | null
  mordida_abierta_post_mm?: number | null
  linea_media?: LineaMedia | null
  clasificacion_angle?: ClasificacionAngle | null
}

// --------------------------------------------------------------------------------
// 5. Erupcion y denticion.
// --------------------------------------------------------------------------------

export interface PediatricEruptionDentitionOut {
  id: string
  encounter_id: string
  secuencia_normal: boolean | null
  perdida_prematura: boolean | null
  retencion_prolongada: boolean | null
  erupcion_retardada: boolean | null
  falta_contacto_proximal: boolean | null
  malposicion_dentaria: boolean | null
  otras_anormalidades: string | null
  edad_dental: string | null
  estado_general_higiene: string | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface PediatricEruptionDentitionCreateInput {
  encounter_id: string
  secuencia_normal?: boolean | null
  perdida_prematura?: boolean | null
  retencion_prolongada?: boolean | null
  erupcion_retardada?: boolean | null
  falta_contacto_proximal?: boolean | null
  malposicion_dentaria?: boolean | null
  otras_anormalidades?: string | null
  edad_dental?: string | null
  estado_general_higiene?: string | null
}

export type PediatricEruptionDentitionBooleanField =
  | 'secuencia_normal'
  | 'perdida_prematura'
  | 'retencion_prolongada'
  | 'erupcion_retardada'
  | 'falta_contacto_proximal'
  | 'malposicion_dentaria'

export const ERUPTION_BOOLEAN_FIELDS: {
  key: PediatricEruptionDentitionBooleanField
  label: string
}[] = [
  { key: 'secuencia_normal', label: 'Secuencia de erupcion normal' },
  { key: 'perdida_prematura', label: 'Perdida prematura de dientes temporales' },
  { key: 'retencion_prolongada', label: 'Retencion prolongada de dientes temporales' },
  { key: 'erupcion_retardada', label: 'Erupcion retardada' },
  { key: 'falta_contacto_proximal', label: 'Falta de contacto proximal' },
  { key: 'malposicion_dentaria', label: 'Malposicion dentaria' },
]

/** Tabla de referencia ESTATICA (no capturable), copiada literal de
 * backend/app/modules/pediatric_history/rules.py -- no recalcular. */
export interface ToothChronologyRow {
  diente: string
  erupcion: string
  caida?: string
}

export const PRIMARY_TOOTH_ERUPTION_CHRONOLOGY: ToothChronologyRow[] = [
  { diente: 'Incisivo central', erupcion: '6-10 meses (inferior), 8-12 meses (superior)', caida: '6-7 anos' },
  { diente: 'Incisivo lateral', erupcion: '10-16 meses (inferior), 9-13 meses (superior)', caida: '7-8 anos' },
  { diente: 'Canino', erupcion: '17-23 meses', caida: '10-12 anos' },
  { diente: 'Primer molar', erupcion: '14-18 meses (inferior), 13-19 meses (superior)', caida: '9-11 anos' },
  { diente: 'Segundo molar', erupcion: '23-31 meses (inferior), 25-33 meses (superior)', caida: '10-12 anos' },
]

export const PERMANENT_TOOTH_ERUPTION_CHRONOLOGY: ToothChronologyRow[] = [
  { diente: 'Incisivo central', erupcion: '6-8 anos' },
  { diente: 'Incisivo lateral', erupcion: '7-9 anos' },
  { diente: 'Canino', erupcion: '9-12 anos' },
  { diente: 'Primer premolar', erupcion: '10-12 anos' },
  { diente: 'Segundo premolar', erupcion: '10-12 anos' },
  { diente: 'Primer molar', erupcion: '6-7 anos' },
  { diente: 'Segundo molar', erupcion: '11-13 anos' },
  { diente: 'Tercer molar', erupcion: '17-21 anos' },
]

// --------------------------------------------------------------------------------
// 6. Odontograma pediatrico -- anotaciones por pieza.
// --------------------------------------------------------------------------------

export interface PediatricToothAnnotationOut {
  id: string
  encounter_id: string
  tooth_fdi: string
  anomaly_code: string
  hipoplasia_detail: string | null
  is_active: boolean
  origin: Origin
  created_at: string
}

export interface PediatricToothAnnotationCreateInput {
  encounter_id: string
  tooth_fdi: string
  anomaly_code: string
  hipoplasia_detail?: string | null
}

/** Los dos codigos "especiales" que el overlay dibuja como triangulo (amarillo /
 * verde respectivamente) en vez de badge de texto -- ver
 * backend/app/modules/pediatric_history/rules.py. Codigos fijos del backend, no
 * datos editables del catalogo (a diferencia del label, que si viene del
 * catalogo administrable `pediatric_tooth_anomaly`). */
export const TOOTH_ANOMALY_CONGENITAL_ABSENCE = 'ausente_congenito'
export const TOOTH_ANOMALY_ACQUIRED_ABSENCE = 'ausente_adquirida'

/** Extrae la abreviatura entre parentesis del nombre del catalogo (p.ej.
 * "Hipoplasia (Hip)" -> "Hip") -- evita duplicar el texto de las 8
 * abreviaturas (fu/Gem/Sn/Hip/tr/CEx/MV/PMA) en el frontend; si el catalogo
 * no trae parentesis (p.ej. fue editado desde Catalogos), cae a las primeras
 * letras del codigo. */
export function anomalyAbbreviation(item: { code: string; name: string }): string {
  const match = item.name.match(/\(([^)]+)\)/)
  if (match) return match[1]
  return item.code.slice(0, 3)
}
