import { apiRequest } from '../../api/client'
import type { DiagnosisCreateInput, DiagnosisOut } from './types'

export function listDiagnoses(patientId: string): Promise<DiagnosisOut[]> {
  return apiRequest<DiagnosisOut[]>(`/patients/${patientId}/diagnoses`)
}

export function createDiagnosis(
  patientId: string,
  input: DiagnosisCreateInput,
): Promise<DiagnosisOut> {
  return apiRequest<DiagnosisOut>(`/patients/${patientId}/diagnoses`, {
    method: 'POST',
    body: input,
  })
}

export function annulDiagnosis(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<DiagnosisOut> {
  return apiRequest<DiagnosisOut>(`/patients/${patientId}/diagnoses/${itemId}/annul`, {
    method: 'POST',
    body: { reason },
  })
}
