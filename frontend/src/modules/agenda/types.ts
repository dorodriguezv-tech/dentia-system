export type AppointmentType =
  | 'consulta'
  | 'limpieza'
  | 'restauracion'
  | 'endodoncia'
  | 'extraccion'
  | 'ortodoncia_control'
  | 'protesis'
  | 'urgencia'

export type AppointmentStatus =
  | 'RESERVADA'
  | 'CONFIRMADA'
  | 'EN_SALA'
  | 'EN_ATENCION'
  | 'TERMINADA'
  | 'CANCELADA'
  | 'NO_SHOW'
  | 'REPROGRAMADA'

export interface ProviderOut {
  id: string
  user_id: string
  full_name: string
  color: string
  is_active: boolean
}

export interface ProviderCreateInput {
  user_id: string
  color?: string
}

export interface ResourceOut {
  id: string
  name: string
  is_active: boolean
}

export interface WorkingHoursOut {
  id: string
  provider_id: string
  weekday: number
  start_time: string
  end_time: string
}

export interface WorkingHoursCreateInput {
  weekday: number
  start_time: string
  end_time: string
}

export interface BlockOut {
  id: string
  provider_id: string
  starts_at: string
  ends_at: string
  reason: string | null
}

export interface BlockCreateInput {
  starts_at: string
  ends_at: string
  reason?: string | null
}

export interface AppointmentListItemOut {
  id: string
  patient_id: string
  patient_full_name: string
  provider_id: string
  provider_full_name: string
  provider_color: string
  resource_id: string | null
  resource_name: string | null
  appointment_type: AppointmentType
  starts_at: string
  ends_at: string
  status: AppointmentStatus
  notes: string | null
}

export interface AppointmentOut {
  id: string
  patient_id: string
  provider_id: string
  resource_id: string | null
  appointment_type: AppointmentType
  starts_at: string
  ends_at: string
  status: AppointmentStatus
  notes: string | null
  cancel_reason: string | null
  rescheduled_from_id: string | null
  warnings: string[]
}

export interface AppointmentCreateInput {
  patient_id: string
  provider_id: string
  resource_id?: string | null
  appointment_type: AppointmentType
  starts_at: string
  ends_at?: string | null
  notes?: string | null
}

export interface StatusChangeInput {
  status: AppointmentStatus
  reason?: string | null
}

export interface RescheduleInput {
  starts_at: string
  ends_at?: string | null
  provider_id?: string | null
  resource_id?: string | null
  reason?: string | null
}

export interface WaitlistOut {
  id: string
  patient_id: string
  provider_id: string | null
  notes: string | null
  resolved: boolean
  resolved_at: string | null
}

export interface WaitlistCreateInput {
  patient_id: string
  provider_id?: string | null
  notes?: string | null
}
