import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '../modules/auth/store'
import * as reportsApi from '../modules/reports/api'
import type { DashboardOut } from '../modules/reports/types'
import { HomePage } from './HomePage'

vi.mock('../modules/reports/api')

function renderHome() {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function setAuthState(roleCode: string) {
  useAuthStore.setState({
    user: {
      id: 'u1',
      email: 'u@example.com',
      full_name: 'Usuario de prueba',
      is_active: true,
      mfa_enabled: false,
      mfa_setup_required: false,
      ai_enabled: true,
    },
    clinics: [
      {
        clinic: { id: 'c1', name: 'Sucursal Centro' },
        role: { code: roleCode, name: roleCode },
      },
    ],
    activeClinicId: 'c1',
  })
}

describe('HomePage', () => {
  beforeEach(() => {
    vi.mocked(reportsApi.getDashboard).mockReset()
  })

  it('muestra solo las secciones que trae el tablero para caja', async () => {
    setAuthState('caja')
    const dashboard: DashboardOut = {
      patients: { active_patients: 10, new_last_30_days: 2 },
      agenda_today: null,
      treatment: null,
      billing: { balance_due_total: '500.00', cash_session_open: true },
      ai_usage: null,
    }
    vi.mocked(reportsApi.getDashboard).mockResolvedValue(dashboard)
    renderHome()

    expect(await screen.findByText('Pacientes')).toBeInTheDocument()
    expect(screen.getByText('Cobranza')).toBeInTheDocument()
    expect(screen.queryByText('Agenda de hoy')).not.toBeInTheDocument()
    expect(screen.queryByText('Tratamientos')).not.toBeInTheDocument()
    expect(screen.queryByText('Asistente de IA')).not.toBeInTheDocument()
    // caja tiene reports.read -> debe ver el enlace a reportes completos.
    expect(screen.getByText('Ver reportes completos →')).toBeInTheDocument()
  })

  it('no muestra el enlace a reportes completos para un rol sin reports.read', async () => {
    setAuthState('odontologo')
    const dashboard: DashboardOut = {
      patients: { active_patients: 10, new_last_30_days: 2 },
      agenda_today: { total_today: 3, counts_by_status: { RESERVADA: 3 } },
      treatment: { pending_plans: 1, accepted_last_30_days: 0 },
      billing: null,
      ai_usage: { pending_review: 1, accepted_last_30_days: 0, rejected_last_30_days: 0 },
    }
    vi.mocked(reportsApi.getDashboard).mockResolvedValue(dashboard)
    renderHome()

    expect(await screen.findByText('Agenda de hoy')).toBeInTheDocument()
    expect(screen.getByText('Asistente de IA')).toBeInTheDocument()
    expect(screen.queryByText('Cobranza')).not.toBeInTheDocument()
    expect(screen.queryByText('Ver reportes completos →')).not.toBeInTheDocument()
  })
})
