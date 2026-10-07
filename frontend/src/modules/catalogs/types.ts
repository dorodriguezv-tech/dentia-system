export interface CatalogItemOut {
  id: string
  catalog_type: string
  code: string
  name: string
  is_active: boolean
  sort_order: number
  extra: Record<string, unknown>
  updated_at: string
}

export interface CatalogItemCreateInput {
  code: string
  name: string
  sort_order?: number
  extra?: Record<string, unknown>
}

export interface CatalogItemUpdateInput {
  name?: string
  is_active?: boolean
  sort_order?: number
  extra?: Record<string, unknown>
}

export interface CatalogImportSummary {
  created: number
  updated: number
  errors: string[]
}
