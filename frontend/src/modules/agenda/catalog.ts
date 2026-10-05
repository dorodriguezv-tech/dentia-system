import type { AppointmentStatus, AppointmentType } from './types'

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

// Catalogo provisional de tipos de cita (se unifica con el catalogo de procedimientos
// real en la Fase 7, ver docs/PENDIENTES_CLINICOS.md).
export const APPOINTMENT_TYPES: Record<AppointmentType, { label: string; defaultMinutes: number }> = {
  consulta: { label: 'Consulta / valoracion', defaultMinutes: 30 },
  limpieza: { label: 'Limpieza dental', defaultMinutes: 45 },
  restauracion: { label: 'Restauracion (resina/amalgama)', defaultMinutes: 60 },
  endodoncia: { label: 'Endodoncia', defaultMinutes: 90 },
  extraccion: { label: 'Extraccion', defaultMinutes: 45 },
  ortodoncia_control: { label: 'Control de ortodoncia', defaultMinutes: 20 },
  protesis: { label: 'Protesis', defaultMinutes: 60 },
  urgencia: { label: 'Urgencia', defaultMinutes: 30 },
}

export const APPOINTMENT_TYPE_CODES = Object.keys(APPOINTMENT_TYPES) as AppointmentType[]
