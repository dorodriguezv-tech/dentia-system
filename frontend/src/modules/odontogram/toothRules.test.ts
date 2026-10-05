import { describe, expect, it } from 'vitest'
import {
  TOOTH_FDI_PERMANENT,
  TOOTH_FDI_TEMPORARY,
  isAnteriorTooth,
  isUpperTooth,
  toothLayout,
  validSurfacesForTooth,
} from './toothRules'

describe('toothRules', () => {
  it('tiene 32 piezas permanentes y 20 temporales', () => {
    expect(TOOTH_FDI_PERMANENT).toHaveLength(32)
    expect(TOOTH_FDI_TEMPORARY).toHaveLength(20)
  })

  it('identifica piezas superiores e inferiores', () => {
    expect(isUpperTooth(16)).toBe(true)
    expect(isUpperTooth(46)).toBe(false)
  })

  it('identifica piezas anteriores (incisivos y canino)', () => {
    expect(isAnteriorTooth(11)).toBe(true)
    expect(isAnteriorTooth(13)).toBe(true)
    expect(isAnteriorTooth(16)).toBe(false)
  })

  it('calcula las 5 superficies validas de una pieza posterior superior', () => {
    expect(new Set(validSurfacesForTooth(16))).toEqual(new Set(['M', 'D', 'V', 'P', 'O']))
  })

  it('calcula las 5 superficies validas de una pieza anterior inferior', () => {
    expect(new Set(validSurfacesForTooth(41))).toEqual(new Set(['M', 'D', 'V', 'L', 'I']))
  })

  it('ubica mesial hacia la linea media segun el lado de la arcada', () => {
    // 16 se dibuja en la mitad izquierda de la pantalla: mesial mira a la derecha
    expect(toothLayout(16).right).toBe('M')
    expect(toothLayout(16).left).toBe('D')
    // 26 se dibuja en la mitad derecha: mesial mira a la izquierda
    expect(toothLayout(26).left).toBe('M')
    expect(toothLayout(26).right).toBe('D')
  })

  it('ubica vestibular arriba en la arcada superior y abajo en la inferior', () => {
    expect(toothLayout(16).top).toBe('V')
    expect(toothLayout(16).bottom).toBe('P')
    expect(toothLayout(46).top).toBe('L')
    expect(toothLayout(46).bottom).toBe('V')
  })
})
