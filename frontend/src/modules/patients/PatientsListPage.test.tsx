import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '../auth/store'
import * as api from './api'
import { PatientsListPage } from './PatientsListPage'

vi.mock('./api')

function renderPage() {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <PatientsListPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const patient = {
  id: 'p1',
  expediente_number: '000001',
  full_name: 'Jose Perez',
  date_of_birth: '1990-05-20',
  status: 'activo' as const,
  phone: null,
  default_resource_id: null,
  primary_provider_id: null,
}

describe('PatientsListPage', () => {
  beforeEach(() => {
    vi.mocked(api.listPatients).mockReset().mockResolvedValue([patient])
  })

  it('no muestra el filtro "Mis pacientes" para un rol que no atiende pacientes', async () => {
    useAuthStore.setState({
      clinics: [
        {
          clinic: { id: 'clinic-1', name: 'Sucursal Centro' },
          role: { code: 'recepcion', name: 'Recepcion' },
        },
      ],
      activeClinicId: 'clinic-1',
    })
    renderPage()
    await screen.findByText('Jose Perez')
    expect(screen.queryByText('Mis pacientes')).not.toBeInTheDocument()
  })

  it('un odontologo puede filtrar por "Mis pacientes" (B3)', async () => {
    useAuthStore.setState({
      clinics: [
        {
          clinic: { id: 'clinic-1', name: 'Sucursal Centro' },
          role: { code: 'odontologo', name: 'Odontologo' },
        },
      ],
      activeClinicId: 'clinic-1',
    })
    renderPage()
    await screen.findByText('Jose Perez')

    await userEvent.click(screen.getByText('Mis pacientes'))

    await waitFor(() => expect(api.listPatients).toHaveBeenCalledWith(undefined, true))
  })
})
