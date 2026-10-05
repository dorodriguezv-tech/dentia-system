import { describe, expect, it } from 'vitest'
import { addDays, combineDateAndTime, monthGridDays, startOfWeek, toDateKey } from './dateUtils'

describe('dateUtils', () => {
  it('toDateKey formatea como YYYY-MM-DD', () => {
    expect(toDateKey(new Date(2026, 10, 2))).toBe('2026-11-02') // noviembre = mes 10
  })

  it('startOfWeek regresa el lunes de esa semana', () => {
    const wednesday = new Date(2026, 10, 4) // miercoles 4 de noviembre de 2026
    expect(toDateKey(startOfWeek(wednesday))).toBe('2026-11-02')
  })

  it('startOfWeek de un lunes se queda igual', () => {
    const monday = new Date(2026, 10, 2)
    expect(toDateKey(startOfWeek(monday))).toBe('2026-11-02')
  })

  it('addDays suma o resta dias correctamente', () => {
    const base = new Date(2026, 10, 2)
    expect(toDateKey(addDays(base, 5))).toBe('2026-11-07')
    expect(toDateKey(addDays(base, -2))).toBe('2026-10-31')
  })

  it('monthGridDays siempre regresa 42 dias empezando en lunes', () => {
    const days = monthGridDays(new Date(2026, 10, 15))
    expect(days).toHaveLength(42)
    expect(days[0].getDay()).toBe(1) // lunes
  })

  it('combineDateAndTime combina la fecha con la hora dada', () => {
    const result = combineDateAndTime(new Date(2026, 10, 2, 23, 59), 9, 30)
    expect(result.getHours()).toBe(9)
    expect(result.getMinutes()).toBe(30)
    expect(toDateKey(result)).toBe('2026-11-02')
  })
})
