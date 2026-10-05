import { API_BASE_URL, apiRequest } from '../../api/client'
import type {
  ContactCreateInput,
  ContactOut,
  DuplicateCandidateOut,
  DuplicateCheckInput,
  PatientCreateInput,
  PatientListItemOut,
  PatientOut,
  PatientSummaryOut,
  PatientUpdateInput,
  StatusCode,
} from './types'

export function listPatients(status?: StatusCode): Promise<PatientListItemOut[]> {
  const query = status ? `?status=${status}` : ''
  return apiRequest<PatientListItemOut[]>(`/patients${query}`)
}

export function searchPatients(q: string, signal?: AbortSignal): Promise<PatientListItemOut[]> {
  return apiRequest<PatientListItemOut[]>(`/patients/search?q=${encodeURIComponent(q)}`, {
    signal,
  })
}

export function checkDuplicates(input: DuplicateCheckInput): Promise<DuplicateCandidateOut[]> {
  return apiRequest<DuplicateCandidateOut[]>('/patients/duplicates-check', {
    method: 'POST',
    body: input,
  })
}

export function createPatient(input: PatientCreateInput): Promise<PatientOut> {
  return apiRequest<PatientOut>('/patients', { method: 'POST', body: input })
}

export function getPatient(patientId: string): Promise<PatientOut> {
  return apiRequest<PatientOut>(`/patients/${patientId}`)
}

export function getPatientSummary(patientId: string): Promise<PatientSummaryOut> {
  return apiRequest<PatientSummaryOut>(`/patients/${patientId}/summary`)
}

export function updatePatient(patientId: string, input: PatientUpdateInput): Promise<PatientOut> {
  return apiRequest<PatientOut>(`/patients/${patientId}`, { method: 'PATCH', body: input })
}

export function listContacts(patientId: string): Promise<ContactOut[]> {
  return apiRequest<ContactOut[]>(`/patients/${patientId}/contacts`)
}

export function createContact(patientId: string, input: ContactCreateInput): Promise<ContactOut> {
  return apiRequest<ContactOut>(`/patients/${patientId}/contacts`, {
    method: 'POST',
    body: input,
  })
}

export function deleteContact(patientId: string, contactId: string): Promise<void> {
  return apiRequest<void>(`/patients/${patientId}/contacts/${contactId}`, { method: 'DELETE' })
}

export async function uploadPatientPhoto(
  patientId: string,
  file: File,
  accessToken: string,
  clinicId: string,
): Promise<PatientOut> {
  const form = new FormData()
  form.append('file', file)

  const response = await fetch(`${API_BASE_URL}/patients/${patientId}/photo`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}`, 'X-Clinic-Id': clinicId },
    body: form,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.message ?? 'No se pudo subir la foto')
  }

  return (await response.json()) as PatientOut
}
