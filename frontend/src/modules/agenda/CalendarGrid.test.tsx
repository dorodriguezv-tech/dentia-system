import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { CalendarGrid } from './CalendarGrid'
import type { WorkingHoursOut } from './types'

// Horario de la clinica (2026-11-02 es lunes, 2026-11-01 es domingo -- mismos
// dias que usa el backend en tests/integration/agenda/test_availability.py):
// lunes 08:00-14:00 y 15:00-19:00 (comida de 14:00 a 15:00); domingo no labora.
const MONDAY = new Date(2026, 10, 2)
const SUNDAY = new Date(2026, 10, 1)

const mondayWorkingHours: WorkingHoursOut[] = [
  { id: 'wh-1', provider_id: 'prov-1', weekday: 0, start_time: '08:00:00', end_time: '14:00:00' },
  { id: 'wh-2', provider_id: 'prov-1', weekday: 0, start_time: '15:00:00', end_time: '19:00:00' },
]

function renderGrid(dates: Date[], workingHours: WorkingHoursOut[]) {
  render(
    <CalendarGrid
      dates={dates}
      appointments={[]}
      workingHours={workingHours}
      onSlotClick={vi.fn()}
      onDropAppointment={vi.fn()}
      onAppointmentClick={vi.fn()}
    />,
  )
}

describe('CalendarGrid', () => {
  it('no sombrea nada dentro del horario laboral', () => {
    renderGrid([MONDAY], mondayWorkingHours)
    const slot = screen.getByRole('button', { name: /lunes.*09:00$/ })
    expect(slot.getAttribute('aria-label')).not.toMatch(/fuera de horario/)
  })

  it('sombrea la hora de comida pero sigue siendo clicable', () => {
    renderGrid([MONDAY], mondayWorkingHours)
    const slot = screen.getByRole('button', { name: /lunes.*14:00$/ })
    expect(slot.getAttribute('aria-label')).toMatch(/fuera de horario laboral, solo urgencias/)
  })

  it('sombrea todo el domingo (no se labora)', () => {
    renderGrid([SUNDAY], mondayWorkingHours)
    const slot = screen.getByRole('button', { name: /domingo.*09:00$/ })
    expect(slot.getAttribute('aria-label')).toMatch(/fuera de horario/)
  })

  it('sin horario cargado (p. ej. agrupando por gabinete) no sombrea nada', () => {
    renderGrid([MONDAY], [])
    const slot = screen.getByRole('button', { name: /lunes.*14:00$/ })
    expect(slot.getAttribute('aria-label')).not.toMatch(/fuera de horario/)
  })
})
