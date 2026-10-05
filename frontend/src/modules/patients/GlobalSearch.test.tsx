import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { GlobalSearch } from './GlobalSearch'
import { useGlobalSearchStore } from './searchStore'

vi.mock('./api')
import * as api from './api'

function renderInRouter() {
  const router = createMemoryRouter(
    [
      { path: '/', element: <GlobalSearch /> },
      { path: '/pacientes/:id', element: <div>Ficha del paciente</div> },
    ],
    { initialEntries: ['/'] },
  )
  render(<RouterProvider router={router} />)
}

describe('GlobalSearch', () => {
  beforeEach(() => {
    useGlobalSearchStore.setState({ open: false })
    vi.mocked(api.searchPatients).mockReset()
  })

  it('no renderiza nada mientras esta cerrada', () => {
    renderInRouter()
    expect(screen.queryByPlaceholderText(/Buscar paciente/)).not.toBeInTheDocument()
  })

  it('Ctrl+K abre el panel y Escape lo cierra', async () => {
    renderInRouter()

    await userEvent.keyboard('{Control>}k{/Control}')
    expect(await screen.findByPlaceholderText(/Buscar paciente/)).toBeInTheDocument()

    await userEvent.keyboard('{Escape}')
    await waitFor(() =>
      expect(screen.queryByPlaceholderText(/Buscar paciente/)).not.toBeInTheDocument(),
    )
  })

  it('escribir dispara la busqueda y seleccionar un resultado navega a la ficha', async () => {
    vi.mocked(api.searchPatients).mockResolvedValue([
      {
        id: 'p1',
        expediente_number: '000001',
        full_name: 'Jose Perez',
        date_of_birth: '1990-05-20',
        status: 'activo',
        phone: null,
      },
    ])

    useGlobalSearchStore.setState({ open: true })
    renderInRouter()

    await userEvent.type(screen.getByPlaceholderText(/Buscar paciente/), 'jose')

    const resultButton = await screen.findByRole('button', { name: /Jose Perez/ })
    await userEvent.click(resultButton)

    expect(await screen.findByText('Ficha del paciente')).toBeInTheDocument()
    expect(useGlobalSearchStore.getState().open).toBe(false)
  })
})
