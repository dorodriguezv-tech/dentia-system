import type { AppointmentStatus } from './types'

/**
 * Copia minima, solo para la interfaz, de backend/app/modules/agenda/rules.py
 * (fuente de verdad real). Los colores por estado (CLAUDE.md Fase 6: "colores por
 * estado desde variables de tema") usan var(--color-status-*), definidas en
 * theme/tokens.css, nunca un #hex fijo (CLAUDE.md sec. 6).
 */
export const STATUS_LABELS: Record<AppointmentStatus, string> = {
  RESERVADA: 'Reservada',
  CONFIRMADA: 'Confirmada',
  EN_SALA: 'En sala',
  EN_ATENCION: 'En atencion',
  TERMINADA: 'Terminada',
  CANCELADA: 'Cancelada',
  NO_SHOW: 'No se presento',
  REPROGRAMADA: 'Reprogramada',
}

export const STATUS_COLORS: Record<AppointmentStatus, string> = {
  RESERVADA: 'var(--color-status-reservada)',
  CONFIRMADA: 'var(--color-status-confirmada)',
  EN_SALA: 'var(--color-status-en-sala)',
  EN_ATENCION: 'var(--color-status-en-atencion)',
  TERMINADA: 'var(--color-status-terminada)',
  CANCELADA: 'var(--color-status-cancelada)',
  NO_SHOW: 'var(--color-status-no-show)',
  REPROGRAMADA: 'var(--color-status-reprogramada)',
}
