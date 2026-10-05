export type StatusCode = 'activo' | 'inactivo' | 'referido' | 'fallecido' | 'bloqueado'
export type SexCode = 'F' | 'M' | 'X'
export type ContactRole = 'guardian' | 'emergency' | 'other'

export interface PatientOut {
  id: string
  expediente_number: string
  first_name: string
  last_name_paternal: string
  last_name_maternal: string | null
  full_name: string
  date_of_birth: string
  sex: SexCode | null
  phone: string | null
  email: string | null
  address: string | null
  status: StatusCode
  has_photo: boolean
}

export interface PatientListItemOut {
  id: string
  expediente_number: string
  full_name: string
  date_of_birth: string
  status: StatusCode
  phone: string | null
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
  phone?: string | null
  email?: string | null
  address?: string | null
}

export interface PatientUpdateInput {
  first_name?: string
  last_name_paternal?: string
  last_name_maternal?: string | null
  sex?: SexCode | null
  phone?: string | null
  email?: string | null
  address?: string | null
  status?: StatusCode
  status_reason?: string
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
