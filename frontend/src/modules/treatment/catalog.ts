import type { PlanStatus, Priority } from './types'

export const PLAN_STATUS_LABELS: Record<PlanStatus, string> = {
  BORRADOR: 'Borrador',
  PRESENTADO: 'Presentado',
  ACEPTADO: 'Aceptado',
  RECHAZADO: 'Rechazado',
  EN_PROGRESO: 'En progreso',
  TERMINADO: 'Terminado',
}

export const PRIORITY_LABELS: Record<Priority, string> = {
  alta: 'Alta',
  media: 'Media',
  baja: 'Baja',
}
