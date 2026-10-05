import { describe, expect, it } from 'vitest'
import {
  contrastRatio,
  deriveHover,
  deriveSoft,
  meetsContrast,
  relativeLuminance,
  hexToRgb,
  suggestContrastingColor,
} from './colorUtils'

describe('contrastRatio', () => {
  it('es maximo entre negro y blanco', () => {
    expect(contrastRatio('#000000', '#FFFFFF')).toBeCloseTo(21, 1)
  })

  it('es 1 para el mismo color', () => {
    expect(contrastRatio('#2BB3A3', '#2BB3A3')).toBeCloseTo(1, 2)
  })

  it('es simetrico', () => {
    const a = contrastRatio('#2BB3A3', '#F7FAFA')
    const b = contrastRatio('#F7FAFA', '#2BB3A3')
    expect(a).toBeCloseTo(b, 4)
  })
})

describe('meetsContrast', () => {
  it('acepta negro sobre blanco', () => {
    expect(meetsContrast('#000000', '#FFFFFF')).toBe(true)
  })

  it('rechaza gris claro sobre blanco', () => {
    expect(meetsContrast('#EEEEEE', '#FFFFFF')).toBe(false)
  })
})

describe('suggestContrastingColor', () => {
  it('alcanza el contraste objetivo sobre fondo claro', () => {
    const suggested = suggestContrastingColor('#EEEEEE', '#FFFFFF')
    expect(contrastRatio(suggested, '#FFFFFF')).toBeGreaterThanOrEqual(4.5)
  })

  it('alcanza el contraste objetivo sobre fondo oscuro', () => {
    const suggested = suggestContrastingColor('#333333', '#000000')
    expect(contrastRatio(suggested, '#000000')).toBeGreaterThanOrEqual(4.5)
  })

  it('no cambia el color si ya pasa', () => {
    expect(suggestContrastingColor('#000000', '#FFFFFF')).toBe('#000000')
  })
})

describe('deriveHover / deriveSoft', () => {
  it('hover es mas oscuro que el primario', () => {
    const primary = '#2BB3A3'
    expect(relativeLuminance(hexToRgb(deriveHover(primary)))).toBeLessThan(
      relativeLuminance(hexToRgb(primary)),
    )
  })

  it('soft es mas claro que el primario', () => {
    const primary = '#2BB3A3'
    expect(relativeLuminance(hexToRgb(deriveSoft(primary)))).toBeGreaterThan(
      relativeLuminance(hexToRgb(primary)),
    )
  })
})
