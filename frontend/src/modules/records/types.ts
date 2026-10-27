export type Severity = 'leve' | 'moderada' | 'severa'

export const SEVERITY_LABELS: Record<Severity, string> = {
  leve: 'Leve',
  moderada: 'Moderada',
  severa: 'Severa',
}

export interface AllergyOut {
  id: string
  encounter_id: string
  substance: string
  reaction: string | null
  severity: Severity
  is_active: boolean
  created_at: string
}

export interface MedicationOut {
  id: string
  encounter_id: string
  name: string
  dose: string | null
  frequency: string | null
  is_active: boolean
  created_at: string
}

export type GlucoseTiming = 'postprandial' | 'preprandial'
export type PatientAttitude = 'cooperador' | 'no_cooperador'

export const GLUCOSE_TIMING_LABELS: Record<GlucoseTiming, string> = {
  postprandial: 'Posprandial',
  preprandial: 'Preprandial',
}

export const PATIENT_ATTITUDE_LABELS: Record<PatientAttitude, string> = {
  cooperador: 'Cooperador',
  no_cooperador: 'No cooperador',
}

export interface VitalSignsOut {
  id: string
  encounter_id: string
  recorded_at: string
  bp_systolic: number | null
  bp_diastolic: number | null
  heart_rate: number | null
  temperature: number | null
  // Fase A (rediseno del expediente, docs/clinica): campos nuevos del formato
  // de signos vitales de la Historia Clinica General.
  height_m: number | null
  weight_kg: number | null
  spo2: number | null
  glucose_index: number | null
  glucose_timing: GlucoseTiming | null
  patient_attitude: PatientAttitude | null
  asa_classification: string | null
  /** Calculado por el backend, solo de lectura. */
  body_mass_index: number | null
}

export interface AllergyCreateInput {
  encounter_id: string
  substance: string
  reaction?: string | null
  severity: Severity
}

export interface MedicationCreateInput {
  encounter_id: string
  name: string
  dose?: string | null
  frequency?: string | null
}

export interface VitalSignsCreateInput {
  encounter_id: string
  bp_systolic?: number | null
  bp_diastolic?: number | null
  heart_rate?: number | null
  temperature?: number | null
  height_m?: number | null
  weight_kg?: number | null
  spo2?: number | null
  glucose_index?: number | null
  glucose_timing?: GlucoseTiming | null
  patient_attitude?: PatientAttitude | null
  asa_classification?: string | null
}

// --------------------------------------------------------------------------------
// Fase A (rediseno del expediente, docs/clinica): Historia Clinica General.
// Shapes exactos tomados de backend/app/modules/records/schemas.py -- no inventar
// campos, cualquier duda se resuelve leyendo ese archivo.
// --------------------------------------------------------------------------------

export type FamilyStatus = 'en_vida' | 'fallecido'
export const FAMILY_STATUS_LABELS: Record<FamilyStatus, string> = {
  en_vida: 'Vive',
  fallecido: 'Fallecido',
}

export type BleedingGumsLevel = 'nunca' | 'algunas_veces' | 'siempre'
export const BLEEDING_GUMS_LABELS: Record<BleedingGumsLevel, string> = {
  nunca: 'Nunca',
  algunas_veces: 'Algunas veces',
  siempre: 'Siempre',
}

export type FoodQualityLevel = 'buena' | 'mala' | 'regular'
export const FOOD_QUALITY_LABELS: Record<FoodQualityLevel, string> = {
  buena: 'Buena',
  mala: 'Mala',
  regular: 'Regular',
}

export type HealthCoverageType = 'civil' | 'derechohabiente' | 'militar'
export const HEALTH_COVERAGE_LABELS: Record<HealthCoverageType, string> = {
  civil: 'Civil',
  derechohabiente: 'Derechohabiente',
  militar: 'Militar',
}

// Correccion Fase A: estado_civil dejo de ser un catalogo cerrado en el backend
// (ahora es texto libre, ver backend/app/modules/records/schemas.py). Estas son
// solo las opciones SUGERIDAS que ofrece el formulario (MARITAL_STATUSES en
// rules.py), mas una opcion "Otro" con texto libre a teclear -- el valor real
// que se envia es `string | null` (ver PersonalNonPathologicalHistoryOut abajo).
export const MARITAL_STATUSES = [
  'soltero',
  'casado',
  'union_libre',
  'divorciado',
  'viudo',
] as const
export type MaritalStatus = (typeof MARITAL_STATUSES)[number]
export const MARITAL_STATUS_LABELS: Record<MaritalStatus, string> = {
  soltero: 'Soltero(a)',
  casado: 'Casado(a)',
  union_libre: 'Unión libre',
  divorciado: 'Divorciado(a)',
  viudo: 'Viudo(a)',
}

export interface FamilyHistoryEntryOut {
  id: string
  encounter_id: string
  relationship_code: string
  status: FamilyStatus
  conditions: Record<string, boolean>
  is_active: boolean
  origin: string
  created_at: string
}

export interface FamilyHistoryEntryCreateInput {
  encounter_id: string
  relationship_code: string
  status: FamilyStatus
  conditions: Record<string, boolean>
}

export interface DiseaseEntry {
  present: boolean
  evolution?: string | null
}

export interface PersonalPathologicalHistoryOut {
  id: string
  encounter_id: string
  dolor_masticar: boolean
  sensibilidad_frio: boolean
  sensibilidad_calor: boolean
  sensibilidad_dulce: boolean
  sensibilidad_localizacion: string | null
  sangrado_encias: BleedingGumsLevel
  dolor_cepillado: boolean
  aftas_ulceras: boolean
  perdida_piezas: boolean
  perdida_piezas_causa: string | null
  anestesia_previa: boolean
  extracciones: boolean
  extracciones_texto: string | null
  complicaciones_operatorias: boolean
  complicaciones_operatorias_texto: string | null
  traumatismo_dental: boolean
  traumatismo_dental_texto: string | null
  infecciones_dentales: boolean
  infecciones_dentales_texto: string | null
  estres: boolean
  estres_texto: string | null
  hospitalizacion_emergencia: boolean
  hospitalizacion_emergencia_texto: string | null
  infecciones_frecuentes: boolean
  infecciones_frecuentes_zona: string | null
  tiempo_evolucion: string | null
  diseases: Record<string, DiseaseEntry>
  is_active: boolean
  origin: string
  created_at: string
}

export type PersonalPathologicalHistoryCreateInput = Omit<
  PersonalPathologicalHistoryOut,
  'id' | 'is_active' | 'origin' | 'created_at'
>

export interface ServiceEntry {
  has: boolean
  notes?: string | null
}

export interface AddictionEntry {
  has: boolean
  detail?: string | null
  fecha_inicio?: string | null
}

export const SERVICIOS_BASICOS_KEYS = [
  'habitacion',
  'luz',
  'agua',
  'drenaje',
  'internet',
  'gas',
  'television',
  'celular',
] as const

export const SERVICIOS_BASICOS_LABELS: Record<(typeof SERVICIOS_BASICOS_KEYS)[number], string> = {
  habitacion: 'Habitación',
  luz: 'Luz',
  agua: 'Agua',
  drenaje: 'Drenaje',
  internet: 'Internet',
  gas: 'Gas',
  television: 'Televisión',
  celular: 'Celular',
}

export const ADICCIONES_KEYS = ['tabaco', 'alcohol', 'estupefacientes'] as const

export const ADICCIONES_LABELS: Record<(typeof ADICCIONES_KEYS)[number], string> = {
  tabaco: 'Tabaco',
  alcohol: 'Alcohol',
  estupefacientes: 'Estupefacientes',
}

export interface PersonalNonPathologicalHistoryOut {
  id: string
  encounter_id: string
  comidas_dia: number | null
  calidad_alimentacion: FoodQualityLevel | null
  agua_litros_dia: number | null
  trastornos_sueno: boolean
  trastornos_sueno_texto: string | null
  cepillados_dia: number | null
  hilo_dental: boolean
  enjuague_bucal: boolean
  deportes: boolean
  deportes_cual: string | null
  derechohabiencia: HealthCoverageType | null
  // Texto libre (ya no un catalogo cerrado) -- ver nota junto a MaritalStatus arriba.
  estado_civil: string | null
  medicamentos_suplementos: boolean
  medicamentos_controlados: boolean
  medicamentos_texto: string | null
  servicios_basicos: Record<string, ServiceEntry>
  adicciones: Record<string, AddictionEntry>
  is_active: boolean
  origin: string
  created_at: string
}

export type PersonalNonPathologicalHistoryCreateInput = Omit<
  PersonalNonPathologicalHistoryOut,
  'id' | 'is_active' | 'origin' | 'created_at'
>

export const SYSTEMS_REVIEW_SYSTEMS = [
  'hematologico',
  'cardiovascular',
  'neurologico',
  'endocrino',
  'respiratorio',
  'genitourinario',
] as const

export type SystemsReviewSystem = (typeof SYSTEMS_REVIEW_SYSTEMS)[number]

export const SYSTEMS_REVIEW_SYSTEM_LABELS: Record<SystemsReviewSystem, string> = {
  hematologico: 'Hematológico',
  cardiovascular: 'Cardiovascular',
  neurologico: 'Neurológico',
  endocrino: 'Endocrino',
  respiratorio: 'Respiratorio',
  genitourinario: 'Genitourinario',
}

/** Campos libres de "Reproductor masculino" (dict[str, unknown] en el backend,
 * sin catalogo): construidos a partir del formato impreso. */
export const REPRODUCTOR_MASCULINO_FIELDS = [
  { key: 'inicio_vida_sexual', label: 'Inicio de vida sexual', type: 'text' },
  { key: 'no_parejas_sexuales', label: 'No. de parejas sexuales', type: 'text' },
  { key: 'examen_prostata', label: 'Examen de próstata', type: 'checkbox' },
  { key: 'examen_prostata_fecha', label: 'Fecha del examen de próstata', type: 'date' },
] as const

/** Campos libres de "Reproductor femenino" (dict[str, unknown] en el backend,
 * sin catalogo): construidos a partir del formato impreso. */
export const REPRODUCTOR_FEMENINO_FIELDS = [
  { key: 'menarca', label: 'Menarca', type: 'text' },
  { key: 'frecuencia_periodo', label: 'Frecuencia del periodo', type: 'text' },
  { key: 'fecha_ultima_menstruacion', label: 'Fecha de última menstruación', type: 'date' },
  { key: 'inicio_vida_sexual', label: 'Inicio de vida sexual', type: 'text' },
  { key: 'no_parejas', label: 'No. de parejas', type: 'text' },
  { key: 'no_embarazos', label: 'No. de embarazos', type: 'text' },
  { key: 'partos', label: 'Partos', type: 'checkbox' },
  { key: 'partos_numero', label: 'No. de partos', type: 'text' },
  { key: 'cesareas', label: 'Cesáreas', type: 'checkbox' },
  { key: 'cesareas_numero', label: 'No. de cesáreas', type: 'text' },
  { key: 'abortos', label: 'Abortos', type: 'checkbox' },
  { key: 'abortos_numero', label: 'No. de abortos', type: 'text' },
  { key: 'lactancia', label: 'Lactancia', type: 'checkbox' },
  { key: 'metodos_anticonceptivos', label: 'Métodos anticonceptivos', type: 'checkbox' },
  { key: 'metodos_anticonceptivos_cual', label: '¿Cuál método anticonceptivo?', type: 'text' },
  { key: 'papanicolau', label: 'Papanicolau', type: 'checkbox' },
  { key: 'papanicolau_fecha', label: 'Fecha del papanicolau', type: 'date' },
] as const

export interface SystemsReviewEntryOut {
  id: string
  encounter_id: string
  hematologico: Record<string, DiseaseEntry>
  cardiovascular: Record<string, DiseaseEntry>
  neurologico: Record<string, DiseaseEntry>
  endocrino: Record<string, DiseaseEntry>
  respiratorio: Record<string, DiseaseEntry>
  genitourinario: Record<string, DiseaseEntry>
  reproductor_masculino: Record<string, unknown>
  reproductor_femenino: Record<string, unknown>
  is_active: boolean
  origin: string
  created_at: string
}

export type SystemsReviewEntryCreateInput = Omit<
  SystemsReviewEntryOut,
  'id' | 'is_active' | 'origin' | 'created_at'
>
