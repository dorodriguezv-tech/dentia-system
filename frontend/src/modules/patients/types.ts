export type StatusCode = 'activo' | 'inactivo' | 'referido' | 'fallecido' | 'bloqueado'
export type SexCode = 'F' | 'M' | 'X'
export type ContactRole = 'guardian' | 'emergency' | 'other'
export type PatientTypeCode = 'pediatrico' | 'adulto'

export interface PatientOut {
  id: string
  expediente_number: string
  first_name: string
  last_name_paternal: string
  last_name_maternal: string | null
  full_name: string
  date_of_birth: string
  sex: SexCode | null
  // Anotacion del expediente (pendiente #73 de docs/PENDIENTES_CLINICOS.md): si no
  // se especifica al crear/editar, el backend la calcula a partir de date_of_birth.
  // Opcional (como birth_place/blood_type/etc. abajo) para no romper fixtures de
  // prueba existentes que construyen un PatientOut sin este campo nuevo.
  patient_type?: PatientTypeCode | null
  phone: string | null
  email: string | null
  address: string | null
  status: StatusCode
  has_photo: boolean
  default_resource_id: string | null
  primary_provider_id: string | null
  // Fase A (rediseno del expediente, docs/clinica): campos compartidos que
  // autollenan la Historia Clinica General y demas documentos impresos
  // (backend/app/modules/patients/schemas.py).
  birth_place?: string | null
  blood_type?: string | null
  education_level?: string | null
  can_read_write?: boolean | null
  religion?: string | null
  ethnic_group?: string | null
  race?: string | null
  occupation?: string | null
  marital_status?: string | null
}

export interface PatientListItemOut {
  id: string
  expediente_number: string
  full_name: string
  date_of_birth: string
  status: StatusCode
  phone: string | null
  default_resource_id: string | null
  primary_provider_id: string | null
}

export interface PatientSummaryOut {
  id: string
  expediente_number: string
  full_name: string
  age: number
  status: StatusCode
  has_photo: boolean
  alerts: string[]
}

export interface PatientCreateInput {
  first_name: string
  last_name_paternal: string
  last_name_maternal?: string | null
  date_of_birth: string
  sex?: SexCode | null
  // null (o ausente) = "Calcular automaticamente" (el backend lo calcula desde
  // date_of_birth); un valor explicito anula ese calculo.
  patient_type?: PatientTypeCode | null
  phone?: string | null
  email?: string | null
  address?: string | null
  default_resource_id?: string | null
  primary_provider_id?: string | null
  birth_place?: string | null
  blood_type?: string | null
  education_level?: string | null
  can_read_write?: boolean | null
  religion?: string | null
  ethnic_group?: string | null
  race?: string | null
  occupation?: string | null
  marital_status?: string | null
}

export interface PatientUpdateInput {
  first_name?: string
  last_name_paternal?: string
  last_name_maternal?: string | null
  sex?: SexCode | null
  // null = no tocar el valor ya guardado (no se recalcula solo); un valor
  // explicito corrige la anotacion a mano.
  patient_type?: PatientTypeCode | null
  phone?: string | null
  email?: string | null
  address?: string | null
  status?: StatusCode
  status_reason?: string
  default_resource_id?: string | null
  primary_provider_id?: string | null
  care_assignment_reason?: string
  birth_place?: string | null
  blood_type?: string | null
  education_level?: string | null
  can_read_write?: boolean | null
  religion?: string | null
  ethnic_group?: string | null
  race?: string | null
  occupation?: string | null
  marital_status?: string | null
}

export interface DuplicateCheckInput {
  first_name: string
  last_name_paternal: string
  last_name_maternal?: string | null
  date_of_birth?: string | null
  phone?: string | null
}

export interface DuplicateCandidateOut {
  id: string
  expediente_number: string
  full_name: string
  date_of_birth: string
  phone: string | null
  similarity: number
}

export interface ContactOut {
  id: string
  role: ContactRole
  full_name: string
  relationship_label: string | null
  phone: string | null
  email: string | null
}

export interface ContactCreateInput {
  role: ContactRole
  full_name: string
  relationship_label?: string | null
  phone?: string | null
  email?: string | null
}

export const STATUS_LABELS: Record<StatusCode, string> = {
  activo: 'Activo',
  inactivo: 'Inactivo',
  referido: 'Referido',
  fallecido: 'Fallecido',
  bloqueado: 'Bloqueado',
}

export const CONTACT_ROLE_LABELS: Record<ContactRole, string> = {
  guardian: 'Tutor o responsable',
  emergency: 'Contacto de emergencia',
  other: 'Otro contacto',
}

export const PATIENT_TYPE_LABELS: Record<PatientTypeCode, string> = {
  pediatrico: 'Pediátrico',
  adulto: 'Adulto',
}

// Corte clinico por defecto, igual que backend/app/modules/patients/rules.py
// (PEDIATRIC_AGE_CUTOFF_YEARS) -- ver pendiente #73 de docs/PENDIENTES_CLINICOS.md.
// Solo para la VISTA PREVIA en pantalla (NewPatientPage/ResumenTab): el valor que
// de verdad se guarda siempre lo calcula el backend al crear/editar.
const PEDIATRIC_AGE_CUTOFF_YEARS = 12

/** Replica `calculate_age` del backend (misma logica de cumpleanos) solo para la
 * vista previa -- no se usa para decidir nada que el servidor no vuelva a decidir. */
function calculateAgeFromDob(dateOfBirth: string, asOf: Date): number | null {
  const parsed = new Date(`${dateOfBirth}T00:00:00`)
  if (Number.isNaN(parsed.getTime())) return null
  let age = asOf.getFullYear() - parsed.getFullYear()
  const hadBirthday =
    asOf.getMonth() > parsed.getMonth() ||
    (asOf.getMonth() === parsed.getMonth() && asOf.getDate() >= parsed.getDate())
  if (!hadBirthday) age -= 1
  return Math.max(age, 0)
}

/** Calcula pediatrico/adulto a partir de la fecha de nacimiento, para la vista
 * previa reactiva del formulario cuando el tipo de paciente esta en "Calcular
 * automaticamente". Devuelve null si la fecha esta vacia o es invalida. */
export function calculatePatientTypeFromDob(dateOfBirth: string): PatientTypeCode | null {
  if (!dateOfBirth) return null
  const age = calculateAgeFromDob(dateOfBirth, new Date())
  if (age === null) return null
  return age < PEDIATRIC_AGE_CUTOFF_YEARS ? 'pediatrico' : 'adulto'
}
