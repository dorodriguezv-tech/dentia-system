import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '../auth/store'
import * as api from './api'
import { ReportsPage } from './ReportsPage'
import type { AccountsReceivableOut, AppointmentsReportOut, PatientsReportOut } from './types'

vi.mock('./api')

function renderPage() {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <ReportsPage />
    </QueryClientProvider>,
  )
}

const patientsReport: PatientsReportOut = {
  date_from: '2026-09-01',
  date_to: '2026-10-01',
  new_patients: 3,
  active_patients: 20,
  rows: [
    {
      patient_id: 'p1',
      expediente_number: 'EXP-0001',
      full_name: 'Jose Perez',
      status: 'activo',
      created_at: '2026-09-15T10:00:00Z',
    },
  ],
}

const appointmentsReport: AppointmentsReportOut = {
  date_from: '2026-09-01',
  date_to: '2026-10-01',
  counts_by_status: { TERMINADA: 4, NO_SHOW: 1 },
  no_show_rate: '20.00',
  rows: [],
}

const accountsReceivableReport: AccountsReceivableOut = {
  as_of: '2026-10-05',
  total_balance_due: '500.00',
  rows: [],
}

describe('ReportsPage', () => {
  beforeEach(() => {
    vi.mocked(api.getPatientsReport).mockReset().mockResolvedValue(patientsReport)
    vi.mocked(api.getAppointmentsReport).mockReset().mockResolvedValue(appointmentsReport)
    vi.mocked(api.getAccountsReceivableReport)
      .mockReset()
      .mockResolvedValue(accountsReceivableReport)
    vi.mocked(api.exportPatientsReport).mockReset().mockResolvedValue(undefined)
    useAuthStore.setState({ user: null, clinics: [], activeClinicId: null })
  })

  it('con AI_ENABLED=false, no ofrece la pestana "Uso del asistente IA"', async () => {
    useAuthStore.setState({
      user: {
        id: 'u1',
        email: 'admin@example.com',
        full_name: 'Admin',
        is_active: true,
        mfa_enabled: false,
        mfa_setup_required: false,
        ai_enabled: false,
      },
      clinics: [],
      activeClinicId: null,
    })

    renderPage()
    await screen.findByText('Jose Perez')

    expect(screen.queryByRole('button', { name: 'Uso del asistente IA' })).not.toBeInTheDocument()
  })

  it('muestra el reporte de pacientes por defecto', async () => {
    renderPage()
    expect(await screen.findByText('Jose Perez')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('cambia de pestaña y carga el reporte de citas', async () => {
    renderPage()
    await screen.findByText('Jose Perez')
    await userEvent.click(screen.getByRole('button', { name: 'Citas' }))
    expect(await screen.findByText('20.00%')).toBeInTheDocument()
  })

  it('oculta el selector de fechas en cuentas por cobrar (es una fotografia actual)', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: 'Cuentas por cobrar' }))
    expect(await screen.findByText('$500.00')).toBeInTheDocument()
    expect(screen.queryByLabelText('Desde')).not.toBeInTheDocument()
  })

  it('exportar CSV llama a la API con el rango seleccionado', async () => {
    renderPage()
    await screen.findByText('Jose Perez')
    await userEvent.click(screen.getByRole('button', { name: 'Exportar CSV' }))
    expect(api.exportPatientsReport).toHaveBeenCalledTimes(1)
  })
})
