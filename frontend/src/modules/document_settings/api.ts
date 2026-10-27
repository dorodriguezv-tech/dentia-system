import { apiRequest, apiRequestFormData } from '../../api/client'
import type { DocumentSettingsOut, DocumentSettingsUpdateInput, LogoSide } from './types'

export function getDocumentSettings(): Promise<DocumentSettingsOut> {
  return apiRequest<DocumentSettingsOut>('/document-settings')
}

export function updateDocumentSettings(
  input: DocumentSettingsUpdateInput,
): Promise<DocumentSettingsOut> {
  return apiRequest<DocumentSettingsOut>('/document-settings', { method: 'PUT', body: input })
}

export function uploadLogo(side: LogoSide, file: File): Promise<DocumentSettingsOut> {
  const form = new FormData()
  form.append('file', file)
  return apiRequestFormData<DocumentSettingsOut>(`/document-settings/logo-${side}`, form)
}
