import { apiRequest, apiRequestBlobUrl, apiRequestFormData } from '../../api/client'
import type { ImageOut, ImageUploadInput } from './types'

export async function uploadImages(patientId: string, input: ImageUploadInput): Promise<ImageOut[]> {
  const formData = new FormData()
  formData.append('encounter_id', input.encounter_id)
  formData.append('study_type', input.study_type)
  if (input.tooth_fdi !== null) formData.append('tooth_fdi', String(input.tooth_fdi))
  if (input.notes) formData.append('notes', input.notes)
  for (const file of input.files) formData.append('files', file, file.name)
  return apiRequestFormData<ImageOut[]>(`/patients/${patientId}/images`, formData)
}

export async function listImages(
  patientId: string,
  filters?: { study_type?: string; tooth_fdi?: number },
): Promise<ImageOut[]> {
  const params = new URLSearchParams()
  if (filters?.study_type) params.set('study_type', filters.study_type)
  if (filters?.tooth_fdi !== undefined) params.set('tooth_fdi', String(filters.tooth_fdi))
  const query = params.toString() ? `?${params.toString()}` : ''
  return apiRequest<ImageOut[]>(`/patients/${patientId}/images${query}`)
}

export async function getImageBlobUrl(imageId: string): Promise<string> {
  return apiRequestBlobUrl(`/images/${imageId}`)
}

export async function getThumbnailBlobUrl(imageId: string): Promise<string> {
  return apiRequestBlobUrl(`/images/${imageId}/thumbnail`)
}

export async function annulImage(imageId: string, reason: string): Promise<ImageOut> {
  return apiRequest<ImageOut>(`/images/${imageId}/annul`, { method: 'POST', body: { reason } })
}
