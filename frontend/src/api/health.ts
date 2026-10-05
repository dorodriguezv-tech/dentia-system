import { apiRequest } from './client'

export interface HealthStatus {
  status: string
}

export function getHealth(): Promise<HealthStatus> {
  return apiRequest<HealthStatus>('/health')
}
