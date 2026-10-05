import { apiRequest, apiRequestBlobUrl } from '../../api/client'
import type {
  ConsentCreateInput,
  ConsentOut,
  DocumentTemplateCreateInput,
  DocumentTemplateOut,
} from './types'

export async function listTemplates(): Promise<DocumentTemplateOut[]> {
  return apiRequest<DocumentTemplateOut[]>('/document-templates')
}

export async function getTemplateHistory(code: string): Promise<DocumentTemplateOut[]> {
  return apiRequest<DocumentTemplateOut[]>(`/document-templates/${code}/history`)
}

export async function createTemplateVersion(
  input: DocumentTemplateCreateInput,
): Promise<DocumentTemplateOut> {
  return apiRequest<DocumentTemplateOut>('/document-templates', { method: 'POST', body: input })
}

export async function listConsents(patientId: string): Promise<ConsentOut[]> {
  return apiRequest<ConsentOut[]>(`/patients/${patientId}/consents`)
}

export async function createConsent(
  patientId: string,
  input: ConsentCreateInput,
): Promise<ConsentOut> {
  return apiRequest<ConsentOut>(`/patients/${patientId}/consents`, {
    method: 'POST',
    body: input,
  })
}

export async function getConsentPdfBlobUrl(consentId: string): Promise<string> {
  return apiRequestBlobUrl(`/consents/${consentId}/pdf`)
}

export async function annulConsent(consentId: string, reason: string): Promise<ConsentOut> {
  return apiRequest<ConsentOut>(`/consents/${consentId}/annul`, {
    method: 'POST',
    body: { reason },
  })
}
