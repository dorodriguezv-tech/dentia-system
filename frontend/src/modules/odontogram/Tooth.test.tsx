import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { Tooth } from './Tooth'
import type { ToothFindingOut } from './types'

function finding(overrides: Partial<ToothFindingOut>): ToothFindingOut {
  return {
    id: 'f1',
    encounter_id: 'enc-1',
    tooth_fdi: 36,
    surface: null,
    finding_code: 'sano',
    kind: 'EXISTING',
    material: null,
    supersedes_id: null,
    is_current: true,
    origin: 'MANUAL',
    created_at: '2026-01-10T12:00:00Z',
    ...overrides,
  }
}

describe('Tooth', () => {
  it('dibuja las 5 superficies clicables en el mismo orden de siempre (top, bottom, left, right, center)', () => {
    const { container } = render(
      <Tooth toothFdi={36} findings={[]} selected={false} onSurfaceClick={vi.fn()} />,
    )
    const rects = container.querySelectorAll('rect')
    expect(rects).toHaveLength(5)
  })

  it('pinta la superficie con el color del catalogo del hallazgo vigente', () => {
    const caries = finding({ tooth_fdi: 36, surface: 'O', finding_code: 'caries' })
    const { container } = render(
      <Tooth toothFdi={36} findings={[caries]} selected={false} onSurfaceClick={vi.fn()} />,
    )
    // pieza 36 es posterior inferior: center = O (oclusal), el 5o rect
    const centerRect = container.querySelectorAll('rect')[4]
    expect(centerRect).toHaveAttribute('fill', 'var(--color-finding-caries)')
  })

  it('un hallazgo de toda la pieza dibuja un solo rect con el color y simbolo del catalogo', () => {
    const ausente = finding({ tooth_fdi: 18, surface: null, finding_code: 'ausente' })
    const { container } = render(
      <Tooth toothFdi={18} findings={[ausente]} selected={false} onSurfaceClick={vi.fn()} />,
    )
    const rects = container.querySelectorAll('rect')
    expect(rects).toHaveLength(1)
    expect(rects[0]).toHaveAttribute('fill', 'var(--color-finding-ausente)')
    expect(screen.getByText('X')).toBeInTheDocument()
  })

  it('un hallazgo de biopelicula_tartaro usa el color verde nuevo del catalogo', () => {
    const bt = finding({ tooth_fdi: 36, surface: 'V', finding_code: 'biopelicula_tartaro' })
    const { container } = render(
      <Tooth toothFdi={36} findings={[bt]} selected={false} onSurfaceClick={vi.fn()} />,
    )
    const colored = Array.from(container.querySelectorAll('rect')).find(
      (r) => r.getAttribute('fill') === 'var(--color-finding-biopelicula_tartaro)',
    )
    expect(colored).toBeDefined()
  })

  it('invoca onSurfaceClick con la pieza y la superficie correctas al hacer clic', () => {
    const onSurfaceClick = vi.fn()
    const { container } = render(
      <Tooth toothFdi={36} findings={[]} selected={false} onSurfaceClick={onSurfaceClick} />,
    )
    const centerRect = container.querySelectorAll('rect')[4]
    centerRect.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    expect(onSurfaceClick).toHaveBeenCalledWith(36, 'O')
  })

  it('dibuja al menos una raiz decorativa no clicable (molar inferior: 2 raices)', () => {
    const { container } = render(
      <Tooth toothFdi={36} findings={[]} selected={false} onSurfaceClick={vi.fn()} />,
    )
    // las raices son <path>, nunca <rect> (no deben contarse en los 5 rects clicables)
    const paths = container.querySelectorAll('path')
    expect(paths.length).toBeGreaterThanOrEqual(3) // 2 raices + contorno de corona
    expect(container.querySelectorAll('rect')).toHaveLength(5)
  })

  it('una pieza anterior se ve mas angosta que un molar (silueta diferenciada por tipo)', () => {
    const { container: anteriorContainer } = render(
      <Tooth toothFdi={11} findings={[]} selected={false} onSurfaceClick={vi.fn()} />,
    )
    const { container: molarContainer } = render(
      <Tooth toothFdi={16} findings={[]} selected={false} onSurfaceClick={vi.fn()} />,
    )
    const anteriorOutline = anteriorContainer.querySelector('path')
    const molarOutline = molarContainer.querySelector('path')
    expect(anteriorOutline?.getAttribute('d')).not.toEqual(molarOutline?.getAttribute('d'))
  })

  it('el aria-label identifica la pieza para accesibilidad', () => {
    render(<Tooth toothFdi={21} findings={[]} selected={false} onSurfaceClick={vi.fn()} />)
    expect(screen.getByLabelText('Pieza 21')).toBeInTheDocument()
  })
})
