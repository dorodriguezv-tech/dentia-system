import type { ColorPalette } from '../modules/branding/types'

/**
 * Copia minima, solo para la interfaz, del catalogo de presets de
 * backend/app/modules/branding/presets.py (fuente de verdad real).
 * Si se agrega un preset ahi, se debe reflejar aqui.
 */
export interface Preset {
  code: string
  name: string
  primary: string
  secondary: string
  accent: string
  bg: string
}

export const DEFAULT_PRESET = 'menta_clinica'

export const PRESETS: Preset[] = [
  {
    code: 'menta_clinica',
    name: 'Menta clinica',
    // #1E7D72, no el teal original #2BB3A3 -- ver backend/app/modules/branding/presets.py.
    primary: '#1E7D72',
    secondary: '#4A90C2',
    accent: '#F2A65A',
    bg: '#F7FAFA',
  },
  {
    code: 'azul_sereno',
    name: 'Azul sereno',
    // #3575B1, no el azul original #3A7FC1 -- no pasaba 4.5:1 WCAG, ver
    // backend/app/modules/branding/presets.py.
    primary: '#3575B1',
    secondary: '#5BBFD6',
    accent: '#F4B860',
    bg: '#F5F8FC',
  },
  {
    code: 'aqua_suave',
    name: 'Aqua suave',
    // #167484, no el original #1FA2B8 -- ver backend/app/modules/branding/presets.py.
    primary: '#167484',
    secondary: '#7CC6A6',
    accent: '#FF9F80',
    bg: '#F4FAFB',
  },
  {
    code: 'lavanda_suave',
    name: 'Lavanda suave',
    // #5C61CA, no el original #7B7FD4 -- ver backend/app/modules/branding/presets.py.
    primary: '#5C61CA',
    secondary: '#5FB3C9',
    accent: '#F2B5A0',
    bg: '#F8F8FD',
  },
  {
    code: 'verde_salvia',
    name: 'Verde salvia',
    // #507B61, no el original #6A9E7F -- ver backend/app/modules/branding/presets.py.
    primary: '#507B61',
    secondary: '#4F8FA8',
    accent: '#E8B04B',
    bg: '#F6F9F6',
  },
  {
    code: 'grafito_profesional',
    name: 'Grafito profesional',
    primary: '#37515F',
    secondary: '#2BB3A3',
    accent: '#F2A65A',
    bg: '#F6F7F8',
  },
]

/** Colores que no varian por preset (ver docs/04_TEMAS_Y_MARCA.md sec. 3). */
export const SHARED_DEFAULTS = {
  surface: '#FFFFFF',
  border: '#DCE6E5',
  text: '#1F2D2B',
  text_muted: '#5E6E6C',
  success: '#3BA55C',
  warning: '#E0A100',
  danger: '#D64545',
}

export const RADIUS_VALUES: Record<'soft' | 'sharp', string> = {
  soft: '10px',
  sharp: '2px',
}

/**
 * Modo oscuro (opcional, docs/04 sec. 1): no hay una variante hecha a mano de
 * cada preset, se invierte el fondo/texto a una base oscura fija y se dejan
 * primary/secondary/accent/success/warning/danger del preset sin cambios.
 */
export const DARK_OVERRIDES = {
  bg: '#121716',
  surface: '#1B211F',
  border: '#2B332F',
  text: '#EDEFEE',
  text_muted: '#A9B3B1',
}

export function findPreset(code: string): Preset | undefined {
  return PRESETS.find((p) => p.code === code)
}

export function fullPalette(presetCode: string): ColorPalette {
  const preset = findPreset(presetCode) ?? PRESETS[0]
  return {
    primary: preset.primary,
    secondary: preset.secondary,
    accent: preset.accent,
    bg: preset.bg,
    ...SHARED_DEFAULTS,
  }
}
