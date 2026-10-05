import type { StudyType } from './types'

/**
 * Copia minima, solo para la interfaz, del catalogo de
 * backend/app/modules/imaging/rules.py (fuente de verdad real).
 */
export const STUDY_TYPE_LABELS: Record<StudyType, string> = {
  intraoral: 'Intraoral',
  extraoral: 'Extraoral',
  periapical: 'Periapical',
  bitewing: 'Bitewing (aleta de mordida)',
  panoramica: 'Panoramica',
  cefalometria: 'Cefalometria',
}

export const STUDY_TYPES = Object.keys(STUDY_TYPE_LABELS) as StudyType[]
