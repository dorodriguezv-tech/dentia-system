import { API_BASE_URL, apiRequest } from '../../api/client'
import type { BrandingOut, BrandingUpdateInput } from './types'

export function getBranding(): Promise<BrandingOut> {
  return apiRequest<BrandingOut>('/branding', { auth: false })
}

export function updateBranding(input: BrandingUpdateInput): Promise<BrandingOut> {
  return apiRequest<BrandingOut>('/branding', { method: 'PUT', body: input })
}

export async function uploadLogo(
  file: File,
  accessToken: string,
  clinicId: string,
): Promise<BrandingOut> {
  const form = new FormData()
  form.append('file', file)

  const response = await fetch(`${API_BASE_URL}/branding/logo`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}`, 'X-Clinic-Id': clinicId },
    body: form,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => null)
    throw new Error(error?.message ?? 'No se pudo subir el logo')
  }

  return (await response.json()) as BrandingOut
}
