import type { FindingCode } from './types'

/**
 * Copia minima, solo para la interfaz, del catalogo de hallazgos de
 * backend/app/modules/odontogram/finding_catalog.py (fuente de verdad real).
 * El color se referencia como variable CSS (--color-finding-*, definida en
 * theme/tokens.css con el mismo valor) en vez de un #hex fijo, por CLAUDE.md sec. 6.
 */
export const FINDING_CATALOG: Record<FindingCode, { label: string; color: string; symbol: string }> = {
  sano: { label: 'Sano', color: 'var(--color-finding-sano)', symbol: '' },
  caries: { label: 'Caries', color: 'var(--color-finding-caries)', symbol: 'C' },
  restauracion: {
    label: 'Restauracion',
    color: 'var(--color-finding-restauracion)',
    symbol: 'R',
  },
  corona: { label: 'Corona', color: 'var(--color-finding-corona)', symbol: 'CO' },
  endodoncia: { label: 'Endodoncia', color: 'var(--color-finding-endodoncia)', symbol: 'E' },
  ausente: { label: 'Ausente', color: 'var(--color-finding-ausente)', symbol: 'X' },
  extraccion_indicada: {
    label: 'Extraccion indicada',
    color: 'var(--color-finding-extraccion_indicada)',
    symbol: 'XI',
  },
  implante: { label: 'Implante', color: 'var(--color-finding-implante)', symbol: 'IM' },
  protesis_fija: {
    label: 'Protesis fija',
    color: 'var(--color-finding-protesis_fija)',
    symbol: 'PF',
  },
  sellador: { label: 'Sellador', color: 'var(--color-finding-sellador)', symbol: 'S' },
  fractura: { label: 'Fractura', color: 'var(--color-finding-fractura)', symbol: 'FX' },
  movilidad: { label: 'Movilidad', color: 'var(--color-finding-movilidad)', symbol: 'MO' },
  biopelicula_tartaro: {
    label: 'Biopelicula y tartaro dental',
    color: 'var(--color-finding-biopelicula_tartaro)',
    symbol: 'BT',
  },
}

export const FINDING_CODES = Object.keys(FINDING_CATALOG) as FindingCode[]
