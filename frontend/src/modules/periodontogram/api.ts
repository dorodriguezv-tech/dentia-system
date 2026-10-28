import { apiRequest, apiRequestBlobUrl } from '../../api/client'
import type {
  IndexType,
  IndicesSummaryOut,
  OcclusalContactEntryCreateInput,
  OcclusalContactEntryOut,
  PeriodontalIndexEntryCreateInput,
  PeriodontalIndexEntryOut,
  PeriodontalProbingSiteCreateInput,
  PeriodontalProbingSiteOut,
  PeriodontalToothMeasurementCreateInput,
  PeriodontalToothMeasurementOut,
  PeriodontogramObservationCreateInput,
  PeriodontogramObservationOut,
} from './types'

const BASE = (patientId: string) => `/patients/${patientId}/periodontogram`

// --------------------------------------------------------------------------------
// 1. Sondeo periodontal -- 6 sitios por pieza.
// --------------------------------------------------------------------------------

export function listProbingSites(patientId: string): Promise<PeriodontalProbingSiteOut[]> {
  return apiRequest<PeriodontalProbingSiteOut[]>(`${BASE(patientId)}/probing-sites`)
}

export function createProbingSite(
  patientId: string,
  input: PeriodontalProbingSiteCreateInput,
): Promise<PeriodontalProbingSiteOut> {
  return apiRequest<PeriodontalProbingSiteOut>(`${BASE(patientId)}/probing-sites`, {
    method: 'POST',
    body: input,
  })
}

export function annulProbingSite(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<PeriodontalProbingSiteOut> {
  return apiRequest<PeriodontalProbingSiteOut>(`${BASE(patientId)}/probing-sites/${itemId}/annul`, {
    method: 'POST',
    body: { reason },
  })
}

// --------------------------------------------------------------------------------
// 2. Medicion por pieza -- movilidad y furcacion.
// --------------------------------------------------------------------------------

export function listToothMeasurements(patientId: string): Promise<PeriodontalToothMeasurementOut[]> {
  return apiRequest<PeriodontalToothMeasurementOut[]>(`${BASE(patientId)}/tooth-measurements`)
}

export function createToothMeasurement(
  patientId: string,
  input: PeriodontalToothMeasurementCreateInput,
): Promise<PeriodontalToothMeasurementOut> {
  return apiRequest<PeriodontalToothMeasurementOut>(`${BASE(patientId)}/tooth-measurements`, {
    method: 'POST',
    body: input,
  })
}

export function annulToothMeasurement(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<PeriodontalToothMeasurementOut> {
  return apiRequest<PeriodontalToothMeasurementOut>(
    `${BASE(patientId)}/tooth-measurements/${itemId}/annul`,
    { method: 'POST', body: { reason } },
  )
}

// --------------------------------------------------------------------------------
// 3. Indices de placa dentobacteriana y gingival.
// --------------------------------------------------------------------------------

export function listIndexEntries(
  patientId: string,
  indexType?: IndexType,
): Promise<PeriodontalIndexEntryOut[]> {
  const query = indexType ? `?index_type=${indexType}` : ''
  return apiRequest<PeriodontalIndexEntryOut[]>(`${BASE(patientId)}/index-entries${query}`)
}

export function createIndexEntry(
  patientId: string,
  input: PeriodontalIndexEntryCreateInput,
): Promise<PeriodontalIndexEntryOut> {
  return apiRequest<PeriodontalIndexEntryOut>(`${BASE(patientId)}/index-entries`, {
    method: 'POST',
    body: input,
  })
}

export function annulIndexEntry(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<PeriodontalIndexEntryOut> {
  return apiRequest<PeriodontalIndexEntryOut>(`${BASE(patientId)}/index-entries/${itemId}/annul`, {
    method: 'POST',
    body: { reason },
  })
}

export function getIndicesSummary(patientId: string, encounterId?: string): Promise<IndicesSummaryOut> {
  const query = encounterId ? `?encounter_id=${encounterId}` : ''
  return apiRequest<IndicesSummaryOut>(`${BASE(patientId)}/indices-summary${query}`)
}

// --------------------------------------------------------------------------------
// 4. Tablas de oclusion -- contactos marcados.
// --------------------------------------------------------------------------------

export function listOcclusalContacts(patientId: string): Promise<OcclusalContactEntryOut[]> {
  return apiRequest<OcclusalContactEntryOut[]>(`${BASE(patientId)}/occlusal-contacts`)
}

export function createOcclusalContact(
  patientId: string,
  input: OcclusalContactEntryCreateInput,
): Promise<OcclusalContactEntryOut> {
  return apiRequest<OcclusalContactEntryOut>(`${BASE(patientId)}/occlusal-contacts`, {
    method: 'POST',
    body: input,
  })
}

export function annulOcclusalContact(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<OcclusalContactEntryOut> {
  return apiRequest<OcclusalContactEntryOut>(`${BASE(patientId)}/occlusal-contacts/${itemId}/annul`, {
    method: 'POST',
    body: { reason },
  })
}

// --------------------------------------------------------------------------------
// 5. Observaciones del periodontograma.
// --------------------------------------------------------------------------------

export function listObservations(patientId: string): Promise<PeriodontogramObservationOut[]> {
  return apiRequest<PeriodontogramObservationOut[]>(`${BASE(patientId)}/observations`)
}

export function createObservation(
  patientId: string,
  input: PeriodontogramObservationCreateInput,
): Promise<PeriodontogramObservationOut> {
  return apiRequest<PeriodontogramObservationOut>(`${BASE(patientId)}/observations`, {
    method: 'POST',
    body: input,
  })
}

export function annulObservation(
  patientId: string,
  itemId: string,
  reason: string,
): Promise<PeriodontogramObservationOut> {
  return apiRequest<PeriodontogramObservationOut>(`${BASE(patientId)}/observations/${itemId}/annul`, {
    method: 'POST',
    body: { reason },
  })
}

// --------------------------------------------------------------------------------
// PDF
// --------------------------------------------------------------------------------

export function getPeriodontogramPdfBlobUrl(patientId: string): Promise<string> {
  return apiRequestBlobUrl(`${BASE(patientId)}/pdf`)
}
