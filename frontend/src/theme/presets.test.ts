import { describe, expect, it } from 'vitest'
import { contrastRatio } from './colorUtils'
import { PRESETS, fullPalette } from './presets'

const WCAG_AA_MINIMUM = 4.5

describe('fullPalette', () => {
  it('devuelve los 4 colores de marca del preset mas los compartidos', () => {
    const palette = fullPalette('azul_sereno')
    const preset = PRESETS.find((p) => p.code === 'azul_sereno')!

    expect(palette.primary).toBe(preset.primary)
    expect(palette.secondary).toBe(preset.secondary)
    expect(palette.accent).toBe(preset.accent)
    expect(palette.bg).toBe(preset.bg)
    expect(palette.surface).toBe('#FFFFFF')
  })

  it('cada preset del catalogo tiene una paleta completa y valida', () => {
    for (const preset of PRESETS) {
      const palette = fullPalette(preset.code)
      for (const value of Object.values(palette)) {
        expect(value).toMatch(/^#[0-9A-Fa-f]{6}$/)
      }
    }
  })

  it(
    'el color primario de cada preset pasa WCAG AA (4.5:1) contra blanco y contra ' +
      'su propio bg (regresion de accessibility.spec.ts: azul_sereno, aqua_suave, ' +
      'lavanda_suave y verde_salvia se quedaron con el mismo bug que menta_clinica, ' +
      'ya corregido antes, hasta que una sucursal real lo agarro)',
    () => {
      for (const preset of PRESETS) {
        expect(contrastRatio(preset.primary, '#FFFFFF')).toBeGreaterThanOrEqual(WCAG_AA_MINIMUM)
        expect(contrastRatio(preset.primary, preset.bg)).toBeGreaterThanOrEqual(WCAG_AA_MINIMUM)
      }
    },
  )
})
