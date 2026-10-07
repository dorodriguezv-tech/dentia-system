import { apiRequest, apiRequestBlobUrl, apiRequestFormData } from '../../api/client'
import type {
  CatalogImportSummary,
  CatalogItemCreateInput,
  CatalogItemOut,
  CatalogItemUpdateInput,
} from './types'

export function listCatalogItems(
  catalogType: string,
  includeInactive: boolean,
): Promise<CatalogItemOut[]> {
  const query = includeInactive ? '?include_inactive=true' : ''
  return apiRequest<CatalogItemOut[]>(`/catalogs/${catalogType}${query}`)
}

export function createCatalogItem(
  catalogType: string,
  input: CatalogItemCreateInput,
): Promise<CatalogItemOut> {
  return apiRequest<CatalogItemOut>(`/catalogs/${catalogType}`, { method: 'POST', body: input })
}

export function updateCatalogItem(
  catalogType: string,
  itemId: string,
  input: CatalogItemUpdateInput,
): Promise<CatalogItemOut> {
  return apiRequest<CatalogItemOut>(`/catalogs/${catalogType}/${itemId}`, {
    method: 'PATCH',
    body: input,
  })
}

// Pendiente de B1 (Parte B, Fase 12.2): importar/exportar el catalogo por CSV.
export async function exportCatalogItems(catalogType: string): Promise<void> {
  const blobUrl = await apiRequestBlobUrl(`/catalogs/${catalogType}/export`)
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = `${catalogType}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(blobUrl)
}

export function importCatalogItems(
  catalogType: string,
  file: File,
): Promise<CatalogImportSummary> {
  const formData = new FormData()
  formData.append('file', file, file.name)
  return apiRequestFormData<CatalogImportSummary>(`/catalogs/${catalogType}/import`, formData)
}
