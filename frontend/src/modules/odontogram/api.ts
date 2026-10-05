import { apiRequest } from '../../api/client'
import type { ToothFindingCreateInput, ToothFindingHistoryEntryOut, ToothFindingOut } from './types'

export function getOdontogram(patientId: string, at?: string): Promise<ToothFindingOut[]> {
  const query = at ? `?at=${at}` : ''
  return apiRequest<ToothFindingOut[]>(`/patients/${patientId}/odontogram${query}`)
}

export function createToothFinding(input: ToothFindingCreateInput): Promise<ToothFindingOut> {
  return apiRequest<ToothFindingOut>('/tooth-findings', { method: 'POST', body: input })
}

export function getToothHistory(
  patientId: string,
  toothFdi: number,
): Promise<ToothFindingHistoryEntryOut[]> {
  return apiRequest<ToothFindingHistoryEntryOut[]>(
    `/patients/${patientId}/teeth/${toothFdi}/history`,
  )
}
