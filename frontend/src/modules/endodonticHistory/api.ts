import { apiRequest, apiRequestBlobUrl } from '../../api/client'
import type {
  EndodonticDiagnosisTreatmentCreateInput,
  EndodonticDiagnosisTreatmentOut,
  EndodonticInterrogationCreateInput,
  EndodonticInterrogationOut,
  EndodonticPeriodontalTestCreateInput,
  EndodonticPeriodontalTestOut,
  EndodonticPulpSensitivityTestCreateInput,
  EndodonticPulpSensitivityTestOut,
  EndodonticRadiographicInterpretationCreateInput,
  EndodonticRadiographicInterpretationOut,
  EndodonticToothDiagnosisCodeCreateInput,
  EndodonticToothDiagnosisCodeOut,
  EndodonticToothKind,
  EndodonticWorkingLengthCreateInput,
  EndodonticWorkingLengthOut,
} from './types'

const BASE = (patientId: string) => `/patients/${patientId}/endodontic-history`

// --------------------------------------------------------------------------------
// 1. Interrogatorio + examen intrabucal/extrabucal.
// --------------------------------------------------------------------------------

export function listInterrogations(patientId: string): Promise<EndodonticInterrogationOut[]> {
  return apiRequest<EndodonticInterrogationOut[]>(`${BASE(patientId)}/interrogation`)
}

export function createInterrogation(
  patientId: string,
  input: EndodonticInterrogationCreateInput,
): Promise<EndodonticInterrogationOut> {
  return apiRequest<EndodonticInterrogationOut>(`${BASE(patientId)}/interrogation`, {
    method: 'POST',
    body: input,
  })
}

export function annulInterrogation(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<EndodonticInterrogationOut> {
  return apiRequest<EndodonticInterrogationOut>(
    `${BASE(patientId)}/interrogation/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// 2. Pruebas de sensibilidad pulpar.
// --------------------------------------------------------------------------------

export function listPulpSensitivityTests(
  patientId: string,
): Promise<EndodonticPulpSensitivityTestOut[]> {
  return apiRequest<EndodonticPulpSensitivityTestOut[]>(`${BASE(patientId)}/pulp-sensitivity-test`)
}

export function createPulpSensitivityTest(
  patientId: string,
  input: EndodonticPulpSensitivityTestCreateInput,
): Promise<EndodonticPulpSensitivityTestOut> {
  return apiRequest<EndodonticPulpSensitivityTestOut>(`${BASE(patientId)}/pulp-sensitivity-test`, {
    method: 'POST',
    body: input,
  })
}

export function annulPulpSensitivityTest(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<EndodonticPulpSensitivityTestOut> {
  return apiRequest<EndodonticPulpSensitivityTestOut>(
    `${BASE(patientId)}/pulp-sensitivity-test/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// 3. Pruebas periodontales.
// --------------------------------------------------------------------------------

export function listPeriodontalTests(patientId: string): Promise<EndodonticPeriodontalTestOut[]> {
  return apiRequest<EndodonticPeriodontalTestOut[]>(`${BASE(patientId)}/periodontal-test`)
}

export function createPeriodontalTest(
  patientId: string,
  input: EndodonticPeriodontalTestCreateInput,
): Promise<EndodonticPeriodontalTestOut> {
  return apiRequest<EndodonticPeriodontalTestOut>(`${BASE(patientId)}/periodontal-test`, {
    method: 'POST',
    body: input,
  })
}

export function annulPeriodontalTest(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<EndodonticPeriodontalTestOut> {
  return apiRequest<EndodonticPeriodontalTestOut>(
    `${BASE(patientId)}/periodontal-test/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// 4. Interpretacion radiografica.
// --------------------------------------------------------------------------------

export function listRadiographicInterpretations(
  patientId: string,
): Promise<EndodonticRadiographicInterpretationOut[]> {
  return apiRequest<EndodonticRadiographicInterpretationOut[]>(
    `${BASE(patientId)}/radiographic-interpretation`,
  )
}

export function createRadiographicInterpretation(
  patientId: string,
  input: EndodonticRadiographicInterpretationCreateInput,
): Promise<EndodonticRadiographicInterpretationOut> {
  return apiRequest<EndodonticRadiographicInterpretationOut>(
    `${BASE(patientId)}/radiographic-interpretation`,
    { method: 'POST', body: input },
  )
}

export function annulRadiographicInterpretation(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<EndodonticRadiographicInterpretationOut> {
  return apiRequest<EndodonticRadiographicInterpretationOut>(
    `${BASE(patientId)}/radiographic-interpretation/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// 5. Diagnostico y tratamiento.
// --------------------------------------------------------------------------------

export function listDiagnosisTreatments(
  patientId: string,
): Promise<EndodonticDiagnosisTreatmentOut[]> {
  return apiRequest<EndodonticDiagnosisTreatmentOut[]>(`${BASE(patientId)}/diagnosis-treatment`)
}

export function createDiagnosisTreatment(
  patientId: string,
  input: EndodonticDiagnosisTreatmentCreateInput,
): Promise<EndodonticDiagnosisTreatmentOut> {
  return apiRequest<EndodonticDiagnosisTreatmentOut>(`${BASE(patientId)}/diagnosis-treatment`, {
    method: 'POST',
    body: input,
  })
}

export function annulDiagnosisTreatment(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<EndodonticDiagnosisTreatmentOut> {
  return apiRequest<EndodonticDiagnosisTreatmentOut>(
    `${BASE(patientId)}/diagnosis-treatment/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// 6. Odontograma de diagnostico/evolucion -- 18 codigos por pieza. El GET
// soporta filtrar por `?kind=diagnostico`/`?kind=evolucion` -- se usa para
// separar las dos queries/caches (diagnostico vs. evolucion).
// --------------------------------------------------------------------------------

export function listToothDiagnosisCodes(
  patientId: string,
  kind: EndodonticToothKind,
): Promise<EndodonticToothDiagnosisCodeOut[]> {
  return apiRequest<EndodonticToothDiagnosisCodeOut[]>(
    `${BASE(patientId)}/tooth-diagnosis-code?kind=${kind}`,
  )
}

export function createToothDiagnosisCode(
  patientId: string,
  input: EndodonticToothDiagnosisCodeCreateInput,
): Promise<EndodonticToothDiagnosisCodeOut> {
  return apiRequest<EndodonticToothDiagnosisCodeOut>(`${BASE(patientId)}/tooth-diagnosis-code`, {
    method: 'POST',
    body: input,
  })
}

export function annulToothDiagnosisCode(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<EndodonticToothDiagnosisCodeOut> {
  return apiRequest<EndodonticToothDiagnosisCodeOut>(
    `${BASE(patientId)}/tooth-diagnosis-code/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// 7. Longitud de trabajo + datos de tratamiento.
// --------------------------------------------------------------------------------

export function listWorkingLengths(patientId: string): Promise<EndodonticWorkingLengthOut[]> {
  return apiRequest<EndodonticWorkingLengthOut[]>(`${BASE(patientId)}/working-length`)
}

export function createWorkingLength(
  patientId: string,
  input: EndodonticWorkingLengthCreateInput,
): Promise<EndodonticWorkingLengthOut> {
  return apiRequest<EndodonticWorkingLengthOut>(`${BASE(patientId)}/working-length`, {
    method: 'POST',
    body: input,
  })
}

export function annulWorkingLength(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<EndodonticWorkingLengthOut> {
  return apiRequest<EndodonticWorkingLengthOut>(
    `${BASE(patientId)}/working-length/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// PDF
// --------------------------------------------------------------------------------

export function getEndodonticHistoryPdfBlobUrl(patientId: string): Promise<string> {
  return apiRequestBlobUrl(`${BASE(patientId)}/pdf`)
}
