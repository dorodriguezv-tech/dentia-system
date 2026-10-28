import { apiRequest, apiRequestBlobUrl } from '../../api/client'
import type {
  ConsentCreateInput,
  ConsentOut,
  CounterReferralNoteCreateInput,
  CounterReferralNoteOut,
  DocumentTemplateCreateInput,
  DocumentTemplateOut,
  PrescriptionCreateInput,
  PrescriptionOut,
  ReferralNoteCreateInput,
  ReferralNoteOut,
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

// --------------------------------------------------------------------------------
// Fase D (docs/clinica, "Documentos imprimibles nuevos"): receta, hoja de
// referencia/interconsulta y hoja de contrarreferencia.
// --------------------------------------------------------------------------------

export function listPrescriptions(patientId: string): Promise<PrescriptionOut[]> {
  return apiRequest<PrescriptionOut[]>(`/patients/${patientId}/clinical-documents/prescriptions`)
}

export function createPrescription(
  patientId: string,
  input: PrescriptionCreateInput,
): Promise<PrescriptionOut> {
  return apiRequest<PrescriptionOut>(`/patients/${patientId}/clinical-documents/prescriptions`, {
    method: 'POST',
    body: input,
  })
}

export function getPrescriptionPdfBlobUrl(prescriptionId: string): Promise<string> {
  return apiRequestBlobUrl(`/clinical-documents/prescriptions/${prescriptionId}/pdf`)
}

export function annulPrescription(prescriptionId: string, reason: string): Promise<PrescriptionOut> {
  return apiRequest<PrescriptionOut>(`/clinical-documents/prescriptions/${prescriptionId}/annul`, {
    method: 'POST',
    body: { reason },
  })
}

export function listReferralNotes(patientId: string): Promise<ReferralNoteOut[]> {
  return apiRequest<ReferralNoteOut[]>(`/patients/${patientId}/clinical-documents/referral-notes`)
}

export function createReferralNote(
  patientId: string,
  input: ReferralNoteCreateInput,
): Promise<ReferralNoteOut> {
  return apiRequest<ReferralNoteOut>(`/patients/${patientId}/clinical-documents/referral-notes`, {
    method: 'POST',
    body: input,
  })
}

export function getReferralNotePdfBlobUrl(referralNoteId: string): Promise<string> {
  return apiRequestBlobUrl(`/clinical-documents/referral-notes/${referralNoteId}/pdf`)
}

export function annulReferralNote(referralNoteId: string, reason: string): Promise<ReferralNoteOut> {
  return apiRequest<ReferralNoteOut>(`/clinical-documents/referral-notes/${referralNoteId}/annul`, {
    method: 'POST',
    body: { reason },
  })
}

export function listCounterReferralNotes(patientId: string): Promise<CounterReferralNoteOut[]> {
  return apiRequest<CounterReferralNoteOut[]>(
    `/patients/${patientId}/clinical-documents/counter-referral-notes`,
  )
}

export function createCounterReferralNote(
  patientId: string,
  input: CounterReferralNoteCreateInput,
): Promise<CounterReferralNoteOut> {
  return apiRequest<CounterReferralNoteOut>(
    `/patients/${patientId}/clinical-documents/counter-referral-notes`,
    { method: 'POST', body: input },
  )
}

export function getCounterReferralNotePdfBlobUrl(counterReferralNoteId: string): Promise<string> {
  return apiRequestBlobUrl(`/clinical-documents/counter-referral-notes/${counterReferralNoteId}/pdf`)
}

export function annulCounterReferralNote(
  counterReferralNoteId: string,
  reason: string,
): Promise<CounterReferralNoteOut> {
  return apiRequest<CounterReferralNoteOut>(
    `/clinical-documents/counter-referral-notes/${counterReferralNoteId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

export function getPatientTreatmentsPerformedPdfBlobUrl(patientId: string): Promise<string> {
  return apiRequestBlobUrl(`/patients/${patientId}/procedures-performed/pdf`)
}
