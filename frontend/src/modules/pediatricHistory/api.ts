import { apiRequest, apiRequestBlobUrl } from '../../api/client'
import type {
  PediatricBehaviorMaturityCreateInput,
  PediatricBehaviorMaturityOut,
  PediatricEruptionDentitionCreateInput,
  PediatricEruptionDentitionOut,
  PediatricOcclusionCreateInput,
  PediatricOcclusionOut,
  PediatricOralHabitsCreateInput,
  PediatricOralHabitsOut,
  PediatricPerinatalHistoryCreateInput,
  PediatricPerinatalHistoryOut,
  PediatricToothAnnotationCreateInput,
  PediatricToothAnnotationOut,
} from './types'

const BASE = (patientId: string) => `/patients/${patientId}/pediatric-history`

// --------------------------------------------------------------------------------
// 1. Antecedentes perinatales y primer ano de vida.
// --------------------------------------------------------------------------------

export function listPerinatalHistories(
  patientId: string,
): Promise<PediatricPerinatalHistoryOut[]> {
  return apiRequest<PediatricPerinatalHistoryOut[]>(`${BASE(patientId)}/perinatal-history`)
}

export function createPerinatalHistory(
  patientId: string,
  input: PediatricPerinatalHistoryCreateInput,
): Promise<PediatricPerinatalHistoryOut> {
  return apiRequest<PediatricPerinatalHistoryOut>(`${BASE(patientId)}/perinatal-history`, {
    method: 'POST',
    body: input,
  })
}

export function annulPerinatalHistory(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<PediatricPerinatalHistoryOut> {
  return apiRequest<PediatricPerinatalHistoryOut>(
    `${BASE(patientId)}/perinatal-history/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// 2. Habitos y antecedentes bucales.
// --------------------------------------------------------------------------------

export function listOralHabits(patientId: string): Promise<PediatricOralHabitsOut[]> {
  return apiRequest<PediatricOralHabitsOut[]>(`${BASE(patientId)}/oral-habits`)
}

export function createOralHabits(
  patientId: string,
  input: PediatricOralHabitsCreateInput,
): Promise<PediatricOralHabitsOut> {
  return apiRequest<PediatricOralHabitsOut>(`${BASE(patientId)}/oral-habits`, {
    method: 'POST',
    body: input,
  })
}

export function annulOralHabits(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<PediatricOralHabitsOut> {
  return apiRequest<PediatricOralHabitsOut>(`${BASE(patientId)}/oral-habits/${itemId}/annul`, {
    method: 'POST',
    body: { reason },
  })
}

// --------------------------------------------------------------------------------
// 3. Madurez y conducta.
// --------------------------------------------------------------------------------

export function listBehaviorMaturities(
  patientId: string,
): Promise<PediatricBehaviorMaturityOut[]> {
  return apiRequest<PediatricBehaviorMaturityOut[]>(`${BASE(patientId)}/behavior-maturity`)
}

export function createBehaviorMaturity(
  patientId: string,
  input: PediatricBehaviorMaturityCreateInput,
): Promise<PediatricBehaviorMaturityOut> {
  return apiRequest<PediatricBehaviorMaturityOut>(`${BASE(patientId)}/behavior-maturity`, {
    method: 'POST',
    body: input,
  })
}

export function annulBehaviorMaturity(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<PediatricBehaviorMaturityOut> {
  return apiRequest<PediatricBehaviorMaturityOut>(
    `${BASE(patientId)}/behavior-maturity/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// 4. Oclusion y alineamiento.
// --------------------------------------------------------------------------------

export function listOcclusions(patientId: string): Promise<PediatricOcclusionOut[]> {
  return apiRequest<PediatricOcclusionOut[]>(`${BASE(patientId)}/occlusion`)
}

export function createOcclusion(
  patientId: string,
  input: PediatricOcclusionCreateInput,
): Promise<PediatricOcclusionOut> {
  return apiRequest<PediatricOcclusionOut>(`${BASE(patientId)}/occlusion`, {
    method: 'POST',
    body: input,
  })
}

export function annulOcclusion(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<PediatricOcclusionOut> {
  return apiRequest<PediatricOcclusionOut>(`${BASE(patientId)}/occlusion/${itemId}/annul`, {
    method: 'POST',
    body: { reason },
  })
}

// --------------------------------------------------------------------------------
// 5. Erupcion y denticion.
// --------------------------------------------------------------------------------

export function listEruptionDentitions(
  patientId: string,
): Promise<PediatricEruptionDentitionOut[]> {
  return apiRequest<PediatricEruptionDentitionOut[]>(`${BASE(patientId)}/eruption-dentition`)
}

export function createEruptionDentition(
  patientId: string,
  input: PediatricEruptionDentitionCreateInput,
): Promise<PediatricEruptionDentitionOut> {
  return apiRequest<PediatricEruptionDentitionOut>(`${BASE(patientId)}/eruption-dentition`, {
    method: 'POST',
    body: input,
  })
}

export function annulEruptionDentition(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<PediatricEruptionDentitionOut> {
  return apiRequest<PediatricEruptionDentitionOut>(
    `${BASE(patientId)}/eruption-dentition/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// 6. Odontograma pediatrico -- anotaciones por pieza.
// --------------------------------------------------------------------------------

export function listToothAnnotations(patientId: string): Promise<PediatricToothAnnotationOut[]> {
  return apiRequest<PediatricToothAnnotationOut[]>(`${BASE(patientId)}/tooth-annotation`)
}

export function createToothAnnotation(
  patientId: string,
  input: PediatricToothAnnotationCreateInput,
): Promise<PediatricToothAnnotationOut> {
  return apiRequest<PediatricToothAnnotationOut>(`${BASE(patientId)}/tooth-annotation`, {
    method: 'POST',
    body: input,
  })
}

export function annulToothAnnotation(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<PediatricToothAnnotationOut> {
  return apiRequest<PediatricToothAnnotationOut>(
    `${BASE(patientId)}/tooth-annotation/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// PDF
// --------------------------------------------------------------------------------

export function getPediatricHistoryPdfBlobUrl(patientId: string): Promise<string> {
  return apiRequestBlobUrl(`${BASE(patientId)}/pdf`)
}
