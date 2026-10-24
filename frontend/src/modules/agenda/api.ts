import { apiRequest } from '../../api/client'
import type { EncounterOut } from '../encounters/types'
import type {
  AppointmentCreateInput,
  AppointmentListItemOut,
  AppointmentOut,
  BlockCreateInput,
  BlockOut,
  ProviderCreateInput,
  ProviderOut,
  RescheduleInput,
  ResourceOut,
  ResourceUpdateInput,
  StatusChangeInput,
  WaitlistCreateInput,
  WaitlistOut,
  WorkingHoursCreateInput,
  WorkingHoursOut,
} from './types'

export function listProviders(): Promise<ProviderOut[]> {
  return apiRequest<ProviderOut[]>('/providers')
}

export function createProvider(input: ProviderCreateInput): Promise<ProviderOut> {
  return apiRequest<ProviderOut>('/providers', { method: 'POST', body: input })
}

export function listResources(clinicId?: string, includeInactive?: boolean): Promise<ResourceOut[]> {
  const query = includeInactive ? '?include_inactive=true' : ''
  return apiRequest<ResourceOut[]>(`/resources${query}`, { clinicId })
}

export function createResource(name: string): Promise<ResourceOut> {
  return apiRequest<ResourceOut>('/resources', { method: 'POST', body: { name } })
}

// Pendiente de B1 (Parte B, Fase 12.2): administrar Gabinetes desde Catalogos.
export function updateResource(
  resourceId: string,
  input: ResourceUpdateInput,
): Promise<ResourceOut> {
  return apiRequest<ResourceOut>(`/resources/${resourceId}`, { method: 'PATCH', body: input })
}

export function listWorkingHours(providerId: string): Promise<WorkingHoursOut[]> {
  return apiRequest<WorkingHoursOut[]>(`/providers/${providerId}/working-hours`)
}

export function createWorkingHours(
  providerId: string,
  input: WorkingHoursCreateInput,
): Promise<WorkingHoursOut> {
  return apiRequest<WorkingHoursOut>(`/providers/${providerId}/working-hours`, {
    method: 'POST',
    body: input,
  })
}

export function deleteWorkingHours(providerId: string, itemId: string): Promise<void> {
  return apiRequest<void>(`/providers/${providerId}/working-hours/${itemId}`, {
    method: 'DELETE',
  })
}

export function listBlocks(providerId: string): Promise<BlockOut[]> {
  return apiRequest<BlockOut[]>(`/providers/${providerId}/blocks`)
}

export function createBlock(providerId: string, input: BlockCreateInput): Promise<BlockOut> {
  return apiRequest<BlockOut>(`/providers/${providerId}/blocks`, { method: 'POST', body: input })
}

export function deleteBlock(providerId: string, itemId: string): Promise<void> {
  return apiRequest<void>(`/providers/${providerId}/blocks/${itemId}`, { method: 'DELETE' })
}

export function listAppointments(params: {
  startsFrom: string
  startsTo: string
  providerId?: string | null
  resourceId?: string | null
  patientId?: string | null
}): Promise<AppointmentListItemOut[]> {
  const query = new URLSearchParams({
    starts_from: params.startsFrom,
    starts_to: params.startsTo,
  })
  if (params.providerId) query.set('provider_id', params.providerId)
  if (params.resourceId) query.set('resource_id', params.resourceId)
  if (params.patientId) query.set('patient_id', params.patientId)
  return apiRequest<AppointmentListItemOut[]>(`/appointments?${query.toString()}`)
}

export function createAppointment(input: AppointmentCreateInput): Promise<AppointmentOut> {
  return apiRequest<AppointmentOut>('/appointments', { method: 'POST', body: input })
}

export function changeAppointmentStatus(
  appointmentId: string,
  input: StatusChangeInput,
): Promise<AppointmentOut> {
  return apiRequest<AppointmentOut>(`/appointments/${appointmentId}/status`, {
    method: 'PATCH',
    body: input,
  })
}

export function rescheduleAppointment(
  appointmentId: string,
  input: RescheduleInput,
): Promise<AppointmentOut> {
  return apiRequest<AppointmentOut>(`/appointments/${appointmentId}/reschedule`, {
    method: 'POST',
    body: input,
  })
}

export function startEncounter(appointmentId: string): Promise<EncounterOut> {
  return apiRequest<EncounterOut>(`/appointments/${appointmentId}/start-encounter`, {
    method: 'POST',
  })
}

export function listWaitlist(): Promise<WaitlistOut[]> {
  return apiRequest<WaitlistOut[]>('/waitlist')
}

export function createWaitlistEntry(input: WaitlistCreateInput): Promise<WaitlistOut> {
  return apiRequest<WaitlistOut>('/waitlist', { method: 'POST', body: input })
}

export function resolveWaitlistEntry(itemId: string): Promise<WaitlistOut> {
  return apiRequest<WaitlistOut>(`/waitlist/${itemId}/resolve`, { method: 'POST' })
}
