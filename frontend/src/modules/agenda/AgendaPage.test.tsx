import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '../auth/store'
import { AgendaPage } from './AgendaPage'
import type { AppointmentListItemOut, ProviderOut, ResourceOut } from './types'

vi.mock('./api')
vi.mock('../catalogs/api')
import * as api from './api'
import * as catalogsApi from '../catalogs/api'

const provider: ProviderOut = {
  id: 'prov-1',
  user_id: 'user-1',
  full_name: 'Dra. Gomez',
  color: '#2bb3a3',
  is_active: true,
  default_resource_id: 'res-1',
}

const resource: ResourceOut = { id: 'res-1', name: 'Gabinete 1', is_active: true }

function todayAt(hour: number, minute: number): Date {
  const d = new Date()
  d.setHours(hour, minute, 0, 0)
  return d
}

const appointment: AppointmentListItemOut = {
  id: 'appt-1',
  patient_id: 'pat-1',
  patient_full_name: 'Jose Perez',
  provider_id: 'prov-1',
  provider_full_name: 'Dra. Gomez',
  provider_color: '#2bb3a3',
  resource_id: 'res-1',
  resource_name: 'Gabinete 1',
  appointment_type: 'consulta',
  starts_at: todayAt(10, 0).toISOString(),
  ends_at: todayAt(10, 30).toISOString(),
  status: 'RESERVADA',
  notes: null,
}

function renderPage() {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AgendaPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AgendaPage', () => {
  beforeEach(() => {
    useAuthStore.setState({
      clinics: [
        {
          clinic: { id: 'clinic-1', name: 'Sucursal Centro' },
          role: { code: 'odontologo', name: 'Odontologo' },
        },
      ],
      activeClinicId: 'clinic-1',
    })
    vi.mocked(api.listProviders).mockReset().mockResolvedValue([provider])
    vi.mocked(api.listResources).mockReset().mockResolvedValue([resource])
    vi.mocked(api.listAppointments).mockReset().mockResolvedValue([appointment])
    vi.mocked(api.listWorkingHours).mockReset().mockResolvedValue([])
    vi.mocked(api.changeAppointmentStatus).mockReset()
    vi.mocked(api.createAppointment).mockReset()
    vi.mocked(api.rescheduleAppointment).mockReset()
    vi.mocked(catalogsApi.listCatalogItems).mockReset().mockResolvedValue([
      {
        id: 'cat-1',
        catalog_type: 'appointment_type',
        code: 'consulta',
        name: 'Consulta / valoracion',
        is_active: true,
        sort_order: 0,
        extra: { default_minutes: 30 },
        updated_at: '2026-10-01T00:00:00Z',
      },
    ])
  })

  it('muestra la cita sembrada en la vista de semana', async () => {
    renderPage()
    expect(await screen.findByText(/Jose Perez/)).toBeInTheDocument()
  })

  it('clic en la cita abre el panel de detalle y permite confirmarla', async () => {
    vi.mocked(api.changeAppointmentStatus).mockResolvedValue({
      ...appointment,
      status: 'CONFIRMADA',
      cancel_reason: null,
      rescheduled_from_id: null,
      warnings: [],
    })
    renderPage()

    await userEvent.click(await screen.findByText(/Jose Perez/))
    expect(await screen.findByRole('heading', { name: 'Jose Perez' })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Confirmar' }))

    await waitFor(() =>
      expect(api.changeAppointmentStatus).toHaveBeenCalledWith('appt-1', {
        status: 'CONFIRMADA',
        reason: undefined,
      }),
    )
  })

  it('cancelar exige un motivo', async () => {
    vi.mocked(api.changeAppointmentStatus).mockResolvedValue({
      ...appointment,
      status: 'CANCELADA',
      cancel_reason: 'Paciente aviso',
      rescheduled_from_id: null,
      warnings: [],
    })
    renderPage()

    await userEvent.click(await screen.findByText(/Jose Perez/))
    await userEvent.click(await screen.findByRole('button', { name: 'Cancelar' }))

    const confirmButtons = screen.getAllByRole('button', { name: 'Confirmar' })
    const cancelConfirm = confirmButtons[confirmButtons.length - 1]
    expect(cancelConfirm).toBeDisabled()

    await userEvent.type(screen.getByPlaceholderText('Motivo'), 'Paciente aviso')
    await userEvent.click(cancelConfirm)

    await waitFor(() =>
      expect(api.changeAppointmentStatus).toHaveBeenCalledWith('appt-1', {
        status: 'CANCELADA',
        reason: 'Paciente aviso',
      }),
    )
  })

  it('nueva cita muestra el tipo de cita del catalogo y preselecciona el gabinete del profesional', async () => {
    useAuthStore.setState({
      clinics: [
        {
          clinic: { id: 'clinic-1', name: 'Sucursal Centro' },
          role: { code: 'admin_clinica', name: 'Administrador' },
        },
      ],
      activeClinicId: 'clinic-1',
    })
    renderPage()
    await screen.findByText(/Jose Perez/)

    const slots = await screen.findAllByRole('button', { name: /Agendar cita/ })
    await userEvent.click(slots[0])

    expect(await screen.findByText(/Consulta \/ valoracion/)).toBeInTheDocument()
    const resourceSelect = screen.getByLabelText('Gabinete') as HTMLSelectElement
    expect(resourceSelect.value).toBe('res-1')
  })
})
