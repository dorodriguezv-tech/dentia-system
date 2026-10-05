import { apiRequest, apiRequestBlobUrl } from '../../api/client'
import type {
  ItemCreateInput,
  ItemOut,
  PhaseCreateInput,
  PhaseWithItemsOut,
  PlanCreateInput,
  PlanDetailOut,
  PlanOut,
  PlanStatus,
  ProcedureCatalogCreateInput,
  ProcedureCatalogOut,
  ProcedurePerformedCreateInput,
  ProcedurePerformedOut,
} from './types'

export function listProcedureCatalog(): Promise<ProcedureCatalogOut[]> {
  return apiRequest<ProcedureCatalogOut[]>('/procedure-catalog')
}

export function createProcedureCatalogItem(
  input: ProcedureCatalogCreateInput,
): Promise<ProcedureCatalogOut> {
  return apiRequest<ProcedureCatalogOut>('/procedure-catalog', { method: 'POST', body: input })
}

export function listPlans(patientId: string): Promise<PlanOut[]> {
  return apiRequest<PlanOut[]>(`/patients/${patientId}/treatment-plans`)
}

export function createPlan(input: PlanCreateInput): Promise<PlanOut> {
  return apiRequest<PlanOut>('/treatment-plans', { method: 'POST', body: input })
}

export function getPlanDetail(planId: string): Promise<PlanDetailOut> {
  return apiRequest<PlanDetailOut>(`/treatment-plans/${planId}`)
}

export function changePlanStatus(
  planId: string,
  status: PlanStatus,
  reason?: string,
): Promise<PlanOut> {
  return apiRequest<PlanOut>(`/treatment-plans/${planId}/status`, {
    method: 'PATCH',
    body: { status, reason },
  })
}

export function acceptPlan(
  planId: string,
  acceptedItemIds: string[],
  acceptedByName: string,
): Promise<PlanOut> {
  return apiRequest<PlanOut>(`/treatment-plans/${planId}/accept`, {
    method: 'POST',
    body: { accepted_item_ids: acceptedItemIds, accepted_by_name: acceptedByName },
  })
}

export function addPhase(planId: string, input: PhaseCreateInput): Promise<PhaseWithItemsOut> {
  return apiRequest<PhaseWithItemsOut>(`/treatment-plans/${planId}/phases`, {
    method: 'POST',
    body: input,
  })
}

export function addItem(
  planId: string,
  phaseId: string,
  input: ItemCreateInput,
): Promise<ItemOut> {
  return apiRequest<ItemOut>(`/treatment-plans/${planId}/phases/${phaseId}/items`, {
    method: 'POST',
    body: input,
  })
}

export function annulItem(planId: string, itemId: string, reason: string): Promise<ItemOut> {
  return apiRequest<ItemOut>(`/treatment-plans/${planId}/items/${itemId}/annul`, {
    method: 'POST',
    body: { reason },
  })
}

export function applyDiscount(
  planId: string,
  itemId: string,
  amount: string,
  reason: string,
): Promise<ItemOut> {
  return apiRequest<ItemOut>(`/treatment-plans/${planId}/items/${itemId}/discount`, {
    method: 'POST',
    body: { amount, reason },
  })
}

export function registerPerformed(
  input: ProcedurePerformedCreateInput,
): Promise<ProcedurePerformedOut> {
  return apiRequest<ProcedurePerformedOut>('/procedures-performed', {
    method: 'POST',
    body: input,
  })
}

export function listPerformed(patientId: string): Promise<ProcedurePerformedOut[]> {
  return apiRequest<ProcedurePerformedOut[]>(`/patients/${patientId}/procedures-performed`)
}

/** Blob URL temporal: el PDF exige el mismo token/X-Clinic-Id que el resto de la API
 * (igual que la foto del paciente, apiRequestBlobUrl en api/client.ts), asi que no se
 * puede enlazar directo con <a href>. */
export function getPlanPdfBlobUrl(planId: string): Promise<string> {
  return apiRequestBlobUrl(`/treatment-plans/${planId}/pdf`)
}
