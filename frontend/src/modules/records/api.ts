import { apiRequest } from '../../api/client'
import type {
  AllergyCreateInput,
  AllergyOut,
  MedicalHistoryCreateInput,
  MedicalHistoryOut,
  MedicationCreateInput,
  MedicationOut,
  VitalSignsCreateInput,
  VitalSignsOut,
} from './types'

export function listHistory(patientId: string): Promise<MedicalHistoryOut[]> {
  return apiRequest<MedicalHistoryOut[]>(`/patients/${patientId}/history`)
}

export function createHistory(
  patientId: string,
  input: MedicalHistoryCreateInput,
): Promise<MedicalHistoryOut> {
  return apiRequest<MedicalHistoryOut>(`/patients/${patientId}/history`, {
    method: 'POST',
    body: input,
  })
}

export function annulHistory(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<MedicalHistoryOut> {
  return apiRequest<MedicalHistoryOut>(`/patients/${patientId}/history/${itemId}/annul`, {
    method: 'POST',
    body: { reason },
  })
}

export function listAllergies(patientId: string): Promise<AllergyOut[]> {
  return apiRequest<AllergyOut[]>(`/patients/${patientId}/allergies`)
}

export function createAllergy(patientId: string, input: AllergyCreateInput): Promise<AllergyOut> {
  return apiRequest<AllergyOut>(`/patients/${patientId}/allergies`, {
    method: 'POST',
    body: input,
  })
}

export function annulAllergy(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<AllergyOut> {
  return apiRequest<AllergyOut>(`/patients/${patientId}/allergies/${itemId}/annul`, {
    method: 'POST',
    body: { reason },
  })
}

export function listMedications(patientId: string): Promise<MedicationOut[]> {
  return apiRequest<MedicationOut[]>(`/patients/${patientId}/medications`)
}

export function createMedication(
  patientId: string,
  input: MedicationCreateInput,
): Promise<MedicationOut> {
  return apiRequest<MedicationOut>(`/patients/${patientId}/medications`, {
    method: 'POST',
    body: input,
  })
}

export function annulMedication(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<MedicationOut> {
  return apiRequest<MedicationOut>(`/patients/${patientId}/medications/${itemId}/annul`, {
    method: 'POST',
    body: { reason },
  })
}

export function listVitalSigns(patientId: string): Promise<VitalSignsOut[]> {
  return apiRequest<VitalSignsOut[]>(`/patients/${patientId}/vital-signs`)
}

export function createVitalSigns(
  patientId: string,
  input: VitalSignsCreateInput,
): Promise<VitalSignsOut> {
  return apiRequest<VitalSignsOut>(`/patients/${patientId}/vital-signs`, {
    method: 'POST',
    body: input,
  })
}

export function getPatientAlerts(patientId: string): Promise<string[]> {
  return apiRequest<string[]>(`/patients/${patientId}/alerts`)
}
