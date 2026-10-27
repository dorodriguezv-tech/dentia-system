import { apiRequest, apiRequestBlobUrl } from '../../api/client'
import type {
  AllergyCreateInput,
  AllergyOut,
  FamilyHistoryEntryCreateInput,
  FamilyHistoryEntryOut,
  MedicationCreateInput,
  MedicationOut,
  PersonalNonPathologicalHistoryCreateInput,
  PersonalNonPathologicalHistoryOut,
  PersonalPathologicalHistoryCreateInput,
  PersonalPathologicalHistoryOut,
  SystemsReviewEntryCreateInput,
  SystemsReviewEntryOut,
  VitalSignsCreateInput,
  VitalSignsOut,
} from './types'

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

// --------------------------------------------------------------------------------
// Fase A (rediseno del expediente, docs/clinica): Historia Clinica General.
// --------------------------------------------------------------------------------

export function listFamilyHistory(patientId: string): Promise<FamilyHistoryEntryOut[]> {
  return apiRequest<FamilyHistoryEntryOut[]>(`/patients/${patientId}/general-history/family`)
}

export function createFamilyHistory(
  patientId: string,
  input: FamilyHistoryEntryCreateInput,
): Promise<FamilyHistoryEntryOut> {
  return apiRequest<FamilyHistoryEntryOut>(`/patients/${patientId}/general-history/family`, {
    method: 'POST',
    body: input,
  })
}

export function annulFamilyHistory(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<FamilyHistoryEntryOut> {
  return apiRequest<FamilyHistoryEntryOut>(
    `/patients/${patientId}/general-history/family/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

export function listPathologicalHistory(
  patientId: string,
): Promise<PersonalPathologicalHistoryOut[]> {
  return apiRequest<PersonalPathologicalHistoryOut[]>(
    `/patients/${patientId}/general-history/pathological`,
  )
}

export function createPathologicalHistory(
  patientId: string,
  input: PersonalPathologicalHistoryCreateInput,
): Promise<PersonalPathologicalHistoryOut> {
  return apiRequest<PersonalPathologicalHistoryOut>(
    `/patients/${patientId}/general-history/pathological`,
    { method: 'POST', body: input },
  )
}

export function annulPathologicalHistory(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<PersonalPathologicalHistoryOut> {
  return apiRequest<PersonalPathologicalHistoryOut>(
    `/patients/${patientId}/general-history/pathological/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

export function listNonPathologicalHistory(
  patientId: string,
): Promise<PersonalNonPathologicalHistoryOut[]> {
  return apiRequest<PersonalNonPathologicalHistoryOut[]>(
    `/patients/${patientId}/general-history/non-pathological`,
  )
}

export function createNonPathologicalHistory(
  patientId: string,
  input: PersonalNonPathologicalHistoryCreateInput,
): Promise<PersonalNonPathologicalHistoryOut> {
  return apiRequest<PersonalNonPathologicalHistoryOut>(
    `/patients/${patientId}/general-history/non-pathological`,
    { method: 'POST', body: input },
  )
}

export function annulNonPathologicalHistory(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<PersonalNonPathologicalHistoryOut> {
  return apiRequest<PersonalNonPathologicalHistoryOut>(
    `/patients/${patientId}/general-history/non-pathological/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

export function listSystemsReview(patientId: string): Promise<SystemsReviewEntryOut[]> {
  return apiRequest<SystemsReviewEntryOut[]>(
    `/patients/${patientId}/general-history/systems-review`,
  )
}

export function createSystemsReview(
  patientId: string,
  input: SystemsReviewEntryCreateInput,
): Promise<SystemsReviewEntryOut> {
  return apiRequest<SystemsReviewEntryOut>(
    `/patients/${patientId}/general-history/systems-review`,
    { method: 'POST', body: input },
  )
}

export function annulSystemsReview(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<SystemsReviewEntryOut> {
  return apiRequest<SystemsReviewEntryOut>(
    `/patients/${patientId}/general-history/systems-review/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

export function getGeneralHistoryPdfBlobUrl(patientId: string): Promise<string> {
  return apiRequestBlobUrl(`/patients/${patientId}/general-history/pdf`)
}
