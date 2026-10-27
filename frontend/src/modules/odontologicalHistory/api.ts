import { apiRequest, apiRequestBlobUrl } from '../../api/client'
import type {
  OdontogramDiagnosisDetailCreateInput,
  OdontogramDiagnosisDetailOut,
  OdontologicalExamCreateInput,
  OdontologicalExamOut,
  ParallelometerAnalysisCreateInput,
  ParallelometerAnalysisOut,
  PeriodontalAnamnesisCreateInput,
  PeriodontalAnamnesisOut,
  RadiographicAnalysisCreateInput,
  RadiographicAnalysisOut,
  RemovablePartialDentureDesignCreateInput,
  RemovablePartialDentureDesignOut,
  ToothDiagnosisEntryCreateInput,
  ToothDiagnosisEntryOut,
  ToothTreatmentPlanEntryCreateInput,
  ToothTreatmentPlanEntryOut,
} from './types'

const BASE = (patientId: string) => `/patients/${patientId}/odontological-history`

// --------------------------------------------------------------------------------
// 1. Exploracion cabeza/cuello + biotipo facial + ATM + tejidos blandos.
// --------------------------------------------------------------------------------

export function listOdontologicalExams(patientId: string): Promise<OdontologicalExamOut[]> {
  return apiRequest<OdontologicalExamOut[]>(`${BASE(patientId)}/exam`)
}

export function createOdontologicalExam(
  patientId: string,
  input: OdontologicalExamCreateInput,
): Promise<OdontologicalExamOut> {
  return apiRequest<OdontologicalExamOut>(`${BASE(patientId)}/exam`, {
    method: 'POST',
    body: input,
  })
}

export function annulOdontologicalExam(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<OdontologicalExamOut> {
  return apiRequest<OdontologicalExamOut>(`${BASE(patientId)}/exam/${itemId}/annul`, {
    method: 'POST',
    body: { reason },
  })
}

// --------------------------------------------------------------------------------
// 2. Anamnesis periodontal.
// --------------------------------------------------------------------------------

export function listPeriodontalAnamneses(patientId: string): Promise<PeriodontalAnamnesisOut[]> {
  return apiRequest<PeriodontalAnamnesisOut[]>(`${BASE(patientId)}/periodontal-anamnesis`)
}

export function createPeriodontalAnamnesis(
  patientId: string,
  input: PeriodontalAnamnesisCreateInput,
): Promise<PeriodontalAnamnesisOut> {
  return apiRequest<PeriodontalAnamnesisOut>(`${BASE(patientId)}/periodontal-anamnesis`, {
    method: 'POST',
    body: input,
  })
}

export function annulPeriodontalAnamnesis(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<PeriodontalAnamnesisOut> {
  return apiRequest<PeriodontalAnamnesisOut>(
    `${BASE(patientId)}/periodontal-anamnesis/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// 3. Auxiliares de diagnostico -- analisis radiografico.
// --------------------------------------------------------------------------------

export function listRadiographicAnalyses(patientId: string): Promise<RadiographicAnalysisOut[]> {
  return apiRequest<RadiographicAnalysisOut[]>(`${BASE(patientId)}/radiographic-analysis`)
}

export function createRadiographicAnalysis(
  patientId: string,
  input: RadiographicAnalysisCreateInput,
): Promise<RadiographicAnalysisOut> {
  return apiRequest<RadiographicAnalysisOut>(`${BASE(patientId)}/radiographic-analysis`, {
    method: 'POST',
    body: input,
  })
}

export function annulRadiographicAnalysis(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<RadiographicAnalysisOut> {
  return apiRequest<RadiographicAnalysisOut>(
    `${BASE(patientId)}/radiographic-analysis/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// 4. Odontograma de diagnostico -- datos complementarios.
// --------------------------------------------------------------------------------

export function listOdontogramDiagnosisDetails(
  patientId: string,
): Promise<OdontogramDiagnosisDetailOut[]> {
  return apiRequest<OdontogramDiagnosisDetailOut[]>(
    `${BASE(patientId)}/odontogram-diagnosis-detail`,
  )
}

export function createOdontogramDiagnosisDetail(
  patientId: string,
  input: OdontogramDiagnosisDetailCreateInput,
): Promise<OdontogramDiagnosisDetailOut> {
  return apiRequest<OdontogramDiagnosisDetailOut>(
    `${BASE(patientId)}/odontogram-diagnosis-detail`,
    { method: 'POST', body: input },
  )
}

export function annulOdontogramDiagnosisDetail(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<OdontogramDiagnosisDetailOut> {
  return apiRequest<OdontogramDiagnosisDetailOut>(
    `${BASE(patientId)}/odontogram-diagnosis-detail/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// 5. Analisis con paralelometro.
// --------------------------------------------------------------------------------

export function listParallelometerAnalyses(
  patientId: string,
): Promise<ParallelometerAnalysisOut[]> {
  return apiRequest<ParallelometerAnalysisOut[]>(`${BASE(patientId)}/parallelometer-analysis`)
}

export function createParallelometerAnalysis(
  patientId: string,
  input: ParallelometerAnalysisCreateInput,
): Promise<ParallelometerAnalysisOut> {
  return apiRequest<ParallelometerAnalysisOut>(`${BASE(patientId)}/parallelometer-analysis`, {
    method: 'POST',
    body: input,
  })
}

export function annulParallelometerAnalysis(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<ParallelometerAnalysisOut> {
  return apiRequest<ParallelometerAnalysisOut>(
    `${BASE(patientId)}/parallelometer-analysis/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// 6. Diseno de protesis parcial removible.
// --------------------------------------------------------------------------------

export function listRemovablePartialDentureDesigns(
  patientId: string,
): Promise<RemovablePartialDentureDesignOut[]> {
  return apiRequest<RemovablePartialDentureDesignOut[]>(
    `${BASE(patientId)}/removable-partial-denture-design`,
  )
}

export function createRemovablePartialDentureDesign(
  patientId: string,
  input: RemovablePartialDentureDesignCreateInput,
): Promise<RemovablePartialDentureDesignOut> {
  return apiRequest<RemovablePartialDentureDesignOut>(
    `${BASE(patientId)}/removable-partial-denture-design`,
    { method: 'POST', body: input },
  )
}

export function annulRemovablePartialDentureDesign(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<RemovablePartialDentureDesignOut> {
  return apiRequest<RemovablePartialDentureDesignOut>(
    `${BASE(patientId)}/removable-partial-denture-design/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// 7. Diagnostico por organo dental.
// --------------------------------------------------------------------------------

export function listToothDiagnosisEntries(patientId: string): Promise<ToothDiagnosisEntryOut[]> {
  return apiRequest<ToothDiagnosisEntryOut[]>(`${BASE(patientId)}/tooth-diagnosis`)
}

export function createToothDiagnosisEntry(
  patientId: string,
  input: ToothDiagnosisEntryCreateInput,
): Promise<ToothDiagnosisEntryOut> {
  return apiRequest<ToothDiagnosisEntryOut>(`${BASE(patientId)}/tooth-diagnosis`, {
    method: 'POST',
    body: input,
  })
}

export function annulToothDiagnosisEntry(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<ToothDiagnosisEntryOut> {
  return apiRequest<ToothDiagnosisEntryOut>(`${BASE(patientId)}/tooth-diagnosis/${itemId}/annul`, {
    method: 'POST',
    body: { reason },
  })
}

// --------------------------------------------------------------------------------
// 8. Plan de tratamiento por organo dental.
// --------------------------------------------------------------------------------

export function listToothTreatmentPlanEntries(
  patientId: string,
): Promise<ToothTreatmentPlanEntryOut[]> {
  return apiRequest<ToothTreatmentPlanEntryOut[]>(`${BASE(patientId)}/tooth-treatment-plan`)
}

export function createToothTreatmentPlanEntry(
  patientId: string,
  input: ToothTreatmentPlanEntryCreateInput,
): Promise<ToothTreatmentPlanEntryOut> {
  return apiRequest<ToothTreatmentPlanEntryOut>(`${BASE(patientId)}/tooth-treatment-plan`, {
    method: 'POST',
    body: input,
  })
}

export function annulToothTreatmentPlanEntry(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<ToothTreatmentPlanEntryOut> {
  return apiRequest<ToothTreatmentPlanEntryOut>(
    `${BASE(patientId)}/tooth-treatment-plan/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// PDF
// --------------------------------------------------------------------------------

export function getOdontologicalHistoryPdfBlobUrl(patientId: string): Promise<string> {
  return apiRequestBlobUrl(`${BASE(patientId)}/pdf`)
}
