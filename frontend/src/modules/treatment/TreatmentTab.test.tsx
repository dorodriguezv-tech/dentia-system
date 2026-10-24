import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '../auth/store'
import { TreatmentTab } from './TreatmentTab'

vi.mock('./api')
vi.mock('../encounters/api')
import * as encountersApi from '../encounters/api'
import * as api from './api'

function renderTreatmentTab() {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <TreatmentTab patientId="pat-1" />
    </QueryClientProvider>,
  )
}

describe('TreatmentTab: Nuevo plan sin atenciones (A3/A4)', () => {
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

    vi.mocked(api.listPlans).mockReset().mockResolvedValue([])
    vi.mocked(encountersApi.listPatientEncounters).mockReset().mockResolvedValue([])
  })

  it('ofrece "+ Iniciar atencion nueva" y crea el plan, igual que el expediente', async () => {
    vi.mocked(encountersApi.createEncounter).mockReset().mockResolvedValue({
      id: 'enc-nueva',
      patient_id: 'pat-1',
      professional_id: 'prof-1',
      appointment_id: null,
      chief_complaint: null,
      started_at: new Date().toISOString(),
      ended_at: null,
    })
    vi.mocked(api.createPlan).mockReset().mockResolvedValue({
      id: 'plan-1',
      patient_id: 'pat-1',
      encounter_id: 'enc-nueva',
      professional_id: 'prof-1',
      professional_name: 'Dr. Prueba',
      title: 'Plan nuevo',
      status: 'BORRADOR',
      notes: null,
      accepted_at: null,
      accepted_by_name: null,
      acceptance_type: null,
      rejected_reason: null,
      total: '0.00',
    })

    renderTreatmentTab()

    await userEvent.click(await screen.findByRole('button', { name: 'Nuevo plan' }))

    const select = await screen.findByLabelText('Atencion')
    expect(
      Array.from((select as HTMLSelectElement).options).some((o) =>
        o.textContent?.includes('Iniciar atencion nueva'),
      ),
    ).toBe(true)

    await userEvent.selectOptions(select, '+ Iniciar atencion nueva')
    await waitFor(() => expect(encountersApi.createEncounter).toHaveBeenCalledWith({ patient_id: 'pat-1' }))

    await userEvent.type(screen.getByPlaceholderText('Titulo del plan'), 'Plan nuevo')
    const submitButton = screen.getByRole('button', { name: 'Crear plan' })
    await waitFor(() => expect(submitButton).not.toBeDisabled())
    await userEvent.click(submitButton)

    await waitFor(() =>
      expect(api.createPlan).toHaveBeenCalledWith({
        patient_id: 'pat-1',
        encounter_id: 'enc-nueva',
        title: 'Plan nuevo',
      }),
    )
  })
})
