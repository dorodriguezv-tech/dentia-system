import type { AppointmentStatus } from '@/api/types';

/**
 * M3 (docs/06_APP_MOVIL_V1_1_PARIDAD.md §3, R1): "solo se muestran las transiciones
 * válidas según la máquina de estados de rules.py". Copia deliberada de
 * backend/app/modules/agenda/rules.py (`_ALLOWED_TRANSITIONS`,
 * `REASON_REQUIRED_STATUSES`) — el backend sigue siendo quien autoriza cada
 * cambio; esto solo decide qué botones mostrar sin pedirle al usuario que
 * descubra a prueba y error qué transición es inválida.
 */
const ALLOWED_TRANSITIONS: Record<AppointmentStatus, AppointmentStatus[]> = {
  RESERVADA: ['CONFIRMADA', 'EN_SALA', 'EN_ATENCION', 'CANCELADA', 'NO_SHOW', 'REPROGRAMADA'],
  CONFIRMADA: ['EN_SALA', 'EN_ATENCION', 'CANCELADA', 'NO_SHOW', 'REPROGRAMADA'],
  EN_SALA: ['EN_ATENCION', 'CANCELADA', 'NO_SHOW'],
  EN_ATENCION: ['TERMINADA'],
  TERMINADA: [],
  CANCELADA: [],
  NO_SHOW: [],
  REPROGRAMADA: [],
};

export function canTransition(current: AppointmentStatus, target: AppointmentStatus): boolean {
  return ALLOWED_TRANSITIONS[current]?.includes(target) ?? false;
}

export function isEditable(status: AppointmentStatus): boolean {
  return status === 'RESERVADA' || status === 'CONFIRMADA';
}

export const REASON_REQUIRED_STATUSES: readonly AppointmentStatus[] = ['CANCELADA', 'NO_SHOW'];

export function reasonRequired(target: AppointmentStatus): boolean {
  return REASON_REQUIRED_STATUSES.includes(target);
}
