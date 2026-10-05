import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '../auth/store'
import { PlanDetail } from './PlanDetail'
import type { PlanDetailOut } from './types'

vi.mock('./api')
vi.mock('../encounters/api')
import * as encountersApi from '../encounters/api'
import * as api from './api'

const planPresentado: PlanDetailOut = {
  id: 'plan-1',
  patient_id: 'pat-1',
  encounter_id: 'enc-1',
  professional_id: 'prof-1',
  title: 'Rehabilitacion pieza 46',
  status: 'PRESENTADO',
  notes: null,
  accepted_at: null,
  accepted_by_name: null,
  acceptance_type: null,
  rejected_reason: null,
  total: '2800.00',
  phases: [
    {
      id: 'phase-1',
      name: 'Fase 1: endodoncia',
      sort_order: 1,
      priority: 'alta',
      phase_total: '2800.00',
      items: [
        {
          id: 'item-1',
          phase_id: 'phase-1',
          encounter_id: 'enc-1',
          tooth_fdi: 46,
          surface: 'O',
          procedure_code: 'endodoncia_unirradicular',
          procedure_name: 'Endodoncia unirradicular',
          finding_code: 'endodoncia',
          unit_price: '2800.00',
          quantity: 1,
          alternative: 'A',
          discount_amount: null,
          discount_reason: null,
          accepted: false,
          is_active: true,
          subtotal: '2800.00',
        },
      ],
    },
  ],
}

function renderPlanDetail() {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <PlanDetail planId="plan-1" patientId="pat-1" onBack={() => {}} />
    </QueryClientProvider>,
  )
}

describe('PlanDetail', () => {
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
    vi.mocked(api.getPlanDetail).mockReset().mockResolvedValue(planPresentado)
    vi.mocked(api.listPerformed).mockReset().mockResolvedValue([])
    vi.mocked(api.acceptPlan).mockReset()
    vi.mocked(encountersApi.listPatientEncounters).mockReset().mockResolvedValue([])
  })

  it('muestra las fases, los procedimientos y los totales', async () => {
    renderPlanDetail()
    expect(await screen.findByText('Rehabilitacion pieza 46')).toBeInTheDocument()
    expect(screen.getByText(/Fase 1: endodoncia/)).toBeInTheDocument()
    expect(screen.getByText(/Endodoncia unirradicular/)).toBeInTheDocument()
    expect(screen.getByText(/Presentado/)).toBeInTheDocument()
  })

  it('aceptar el presupuesto marca los items seleccionados y manda el nombre', async () => {
    vi.mocked(api.acceptPlan).mockResolvedValue({
      ...planPresentado,
      status: 'ACEPTADO',
      acceptance_type: 'TOTAL',
      accepted_at: '2026-10-05T12:00:00Z',
      accepted_by_name: 'Jose Perez',
    })
    renderPlanDetail()

    await userEvent.click(await screen.findByRole('button', { name: 'Aceptar presupuesto' }))
    await userEvent.click(screen.getByRole('checkbox'))
    await userEvent.type(
      screen.getByPlaceholderText('Nombre de quien acepta'),
      'Jose Perez',
    )
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar aceptacion' }))

    await waitFor(() =>
      expect(api.acceptPlan).toHaveBeenCalledWith('plan-1', ['item-1'], 'Jose Perez'),
    )
  })
})
