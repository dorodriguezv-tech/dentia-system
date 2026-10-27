import { describe, expect, it } from 'vitest'
import { toothVisualType } from './toothRules'
import { crownScaleX, crownWidth, cuspLobes, rootShapes } from './toothShapes'

describe('toothVisualType', () => {
  it('clasifica incisivos y canino como anterior', () => {
    expect(toothVisualType(11)).toBe('anterior')
    expect(toothVisualType(13)).toBe('anterior') // canino
    expect(toothVisualType(43)).toBe('anterior')
  })

  it('clasifica premolares permanentes (4-5) como premolar', () => {
    expect(toothVisualType(14)).toBe('premolar')
    expect(toothVisualType(45)).toBe('premolar')
  })

  it('clasifica molares permanentes (6-8) como molar', () => {
    expect(toothVisualType(16)).toBe('molar')
    expect(toothVisualType(48)).toBe('molar')
  })

  it('en denticion temporal, las posiciones 4-5 son molares (no hay premolar temporal)', () => {
    expect(toothVisualType(54)).toBe('molar')
    expect(toothVisualType(85)).toBe('molar')
    expect(toothVisualType(51)).toBe('anterior')
  })
})

describe('crownWidth / crownScaleX', () => {
  it('ordena el ancho anterior < premolar < molar', () => {
    expect(crownWidth('anterior')).toBeLessThan(crownWidth('premolar'))
    expect(crownWidth('premolar')).toBeLessThan(crownWidth('molar'))
  })

  it('el molar usa el ancho completo de la caja (sin escalar las 5 superficies)', () => {
    expect(crownWidth('molar')).toBe(44)
    expect(crownScaleX('molar')).toBe(1)
  })

  it('anterior y premolar escalan por debajo de 1', () => {
    expect(crownScaleX('anterior')).toBeLessThan(1)
    expect(crownScaleX('premolar')).toBeLessThan(1)
    expect(crownScaleX('anterior')).toBeGreaterThan(0)
  })
})

describe('cuspLobes', () => {
  it('dibuja mas cuspides en molar que en premolar que en anterior', () => {
    expect(cuspLobes('anterior', 'bottom')).toHaveLength(1)
    expect(cuspLobes('premolar', 'bottom')).toHaveLength(2)
    expect(cuspLobes('molar', 'bottom')).toHaveLength(4)
  })

  it('coloca las cuspides en el borde correcto segun la arcada', () => {
    const upper = cuspLobes('molar', 'bottom') // arcada superior: cuspides abajo (y=41)
    const lower = cuspLobes('molar', 'top') // arcada inferior: cuspides arriba (y=3)
    expect(upper.every((l) => l.cy === 41)).toBe(true)
    expect(lower.every((l) => l.cy === 3)).toBe(true)
  })
})

describe('rootShapes', () => {
  it('anterior y premolar tienen una sola raiz', () => {
    expect(rootShapes('anterior', false, 22, 0)).toHaveLength(1)
    expect(rootShapes('premolar', false, 22, 0)).toHaveLength(1)
  })

  it('molar inferior tiene 2 raices, molar superior 3 (incluye la palatina central)', () => {
    expect(rootShapes('molar', false, 44, 66)).toHaveLength(2)
    expect(rootShapes('molar', true, 22, 0)).toHaveLength(3)
  })

  it('cada raiz es un path valido que empieza en M y termina en Z', () => {
    for (const root of rootShapes('molar', true, 22, 0)) {
      expect(root.d.trim().startsWith('M')).toBe(true)
      expect(root.d.trim().endsWith('Z')).toBe(true)
    }
  })
})
