import { describe, expect, it } from 'vitest'
import { PRESETS, fullPalette } from './presets'

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
})
