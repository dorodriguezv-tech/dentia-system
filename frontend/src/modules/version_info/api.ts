import { apiRequest } from '../../api/client'
import type { VersionInfoOut } from './types'

export function getVersionInfo(): Promise<VersionInfoOut> {
  return apiRequest<VersionInfoOut>('/version-info')
}
