import type { Surface } from './types'

/**
 * Copia minima, solo para la interfaz, de backend/app/modules/odontogram/rules.py
 * (fuente de verdad real): catalogo de piezas FDI y las 5 superficies clicables de
 * cada una, usado para construir la arcada y evitar clics invalidos antes de llamar
 * al backend (que vuelve a validar todo).
 */

const QUADRANTS_PERMANENT = [1, 2, 3, 4]
const QUADRANTS_TEMPORARY = [5, 6, 7, 8]

export const TOOTH_FDI_PERMANENT: number[] = QUADRANTS_PERMANENT.flatMap((q) =>
  [1, 2, 3, 4, 5, 6, 7, 8].map((p) => q * 10 + p),
)
export const TOOTH_FDI_TEMPORARY: number[] = QUADRANTS_TEMPORARY.flatMap((q) =>
  [1, 2, 3, 4, 5].map((p) => q * 10 + p),
)

// Orden de lectura clinico estandar (como si se mirara al paciente de frente): la
// pieza 11 queda arriba de la 41, y la 21 arriba de la 31.
export const UPPER_PERMANENT_ROW = [18, 17, 16, 15, 14, 13, 12, 11, 21, 22, 23, 24, 25, 26, 27, 28]
export const LOWER_PERMANENT_ROW = [48, 47, 46, 45, 44, 43, 42, 41, 31, 32, 33, 34, 35, 36, 37, 38]
export const UPPER_TEMPORARY_ROW = [55, 54, 53, 52, 51, 61, 62, 63, 64, 65]
export const LOWER_TEMPORARY_ROW = [85, 84, 83, 82, 81, 71, 72, 73, 74, 75]

const _UPPER_QUADRANTS = new Set([1, 2, 5, 6])
const _ANTERIOR_POSITIONS = new Set([1, 2, 3])
// Cuadrantes que se dibujan en la mitad izquierda de la pantalla (lado derecho del
// paciente): la mesial de esas piezas mira hacia la derecha (hacia la linea media).
const _QUADRANTS_DISPLAYED_ON_LEFT = new Set([1, 4, 5, 8])

export function isTemporaryTooth(toothFdi: number): boolean {
  return TOOTH_FDI_TEMPORARY.includes(toothFdi)
}

export function isUpperTooth(toothFdi: number): boolean {
  return _UPPER_QUADRANTS.has(Math.floor(toothFdi / 10))
}

export function isAnteriorTooth(toothFdi: number): boolean {
  return _ANTERIOR_POSITIONS.has(toothFdi % 10)
}

export function validSurfacesForTooth(toothFdi: number): Surface[] {
  const surfaces: Surface[] = ['M', 'D', 'V']
  surfaces.push(isUpperTooth(toothFdi) ? 'P' : 'L')
  surfaces.push(isAnteriorTooth(toothFdi) ? 'I' : 'O')
  return surfaces
}

/** Las 5 zonas clicables del SVG, ubicadas anatomicamente (regla visual del chart). */
export interface ToothLayout {
  top: Surface // vestibular siempre arriba
  bottom: Surface // palatino (superior) o lingual (inferior), hacia el hueco entre arcadas
  left: Surface
  right: Surface
  center: Surface // oclusal (posterior) o incisal (anterior)
}

export function toothLayout(toothFdi: number): ToothLayout {
  const upper = isUpperTooth(toothFdi)
  const mesialOnRight = _QUADRANTS_DISPLAYED_ON_LEFT.has(Math.floor(toothFdi / 10))
  return {
    top: upper ? 'V' : 'L',
    bottom: upper ? 'P' : 'V',
    left: mesialOnRight ? 'D' : 'M',
    right: mesialOnRight ? 'M' : 'D',
    center: isAnteriorTooth(toothFdi) ? 'I' : 'O',
  }
}

export type ToothVisualType = 'anterior' | 'premolar' | 'molar'

/**
 * Clasificacion visual de la pieza para la silueta anatomica del odontograma (Fase B,
 * corona + raiz) -- no afecta superficies validas ni el modelo de datos, solo que forma
 * dibuja `Tooth.tsx`.
 * - anterior: incisivos y canino (posiciones 1-3), misma agrupacion que isAnteriorTooth.
 * - premolar: posiciones 4-5 en piezas PERMANENTES unicamente.
 * - molar: posiciones 6-8 permanentes, y tambien 4-5 en piezas TEMPORALES -- la denticion
 *   temporal no tiene premolares: esas posiciones son el primer/segundo molar temporal.
 */
export function toothVisualType(toothFdi: number): ToothVisualType {
  const position = toothFdi % 10
  if (position <= 3) return 'anterior'
  if (isTemporaryTooth(toothFdi)) return 'molar'
  return position <= 5 ? 'premolar' : 'molar'
}

export const SURFACE_LABELS: Record<Surface, string> = {
  O: 'Oclusal',
  M: 'Mesial',
  D: 'Distal',
  V: 'Vestibular',
  L: 'Lingual',
  P: 'Palatino',
  I: 'Incisal',
}
