import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Odontograma } from './Odontograma'
import type { ToothFindingOut } from './types'

vi.mock('./api')
vi.mock('../encounters/api')
import * as encountersApi from '../encounters/api'
import * as api from './api'

const encounter = {
  id: 'enc-1',
  patient_id: 'pat-1',
  professional_id: 'prof-1',
  appointment_id: null,
  chief_complaint: 'Dolor al frio',
  started_at: '2026-01-10T12:00:00Z',
  ended_at: null,
}

const existingCaries: ToothFindingOut = {
  id: 'f1',
  encounter_id: 'enc-1',
  tooth_fdi: 36,
  surface: 'O',
  finding_code: 'caries',
  kind: 'EXISTING',
  material: null,
  supersedes_id: null,
  is_current: true,
  origin: 'MANUAL',
  created_at: '2026-01-10T12:00:00Z',
}

function renderOdontograma(canWrite = true) {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <Odontograma patientId="pat-1" canWrite={canWrite} />
    </QueryClientProvider>,
  )
}

describe('Odontograma', () => {
  beforeEach(() => {
    vi.mocked(api.getOdontogram).mockReset().mockResolvedValue([existingCaries])
    vi.mocked(api.createToothFinding).mockReset()
    vi.mocked(api.getToothHistory).mockReset().mockResolvedValue([])
    vi.mocked(encountersApi.listPatientEncounters).mockReset().mockResolvedValue([encounter])
  })

  it('muestra la pieza 36 con la caries vigente sembrada', async () => {
    renderOdontograma()
    expect(await screen.findByLabelText('Pieza 36')).toBeInTheDocument()
  })

  it('clic en una superficie abre el menu rapido y registra el hallazgo', async () => {
    vi.mocked(api.createToothFinding).mockResolvedValue({
      ...existingCaries,
      id: 'f2',
      finding_code: 'restauracion',
    })
    renderOdontograma()

    const tooth = await screen.findByLabelText('Pieza 36')
    const centerSurface = tooth.querySelectorAll('rect')[4] // top,bottom,left,right,center
    fireEvent.click(centerSurface)

    expect(await screen.findByText('Pieza 36', { selector: 'h3' })).toBeInTheDocument()

    await userEvent.selectOptions(screen.getByRole('combobox'), 'enc-1')
    await userEvent.click(screen.getByRole('button', { name: 'Restauracion' }))
    await userEvent.click(screen.getByRole('button', { name: 'Registrar hallazgo' }))

    await waitFor(() =>
      expect(api.createToothFinding).toHaveBeenCalledWith(
        expect.objectContaining({
          patient_id: 'pat-1',
          tooth_fdi: 36,
          surface: 'O',
          finding_code: 'restauracion',
          encounter_id: 'enc-1',
        }),
        expect.anything(),
      ),
    )
  })

  it('al ver una fecha pasada no se puede editar', async () => {
    renderOdontograma()

    const tooth = await screen.findByLabelText('Pieza 36')
    const centerSurface = tooth.querySelectorAll('rect')[4]
    fireEvent.click(centerSurface)
    expect(await screen.findByText('Pieza 36', { selector: 'h3' })).toBeInTheDocument()

    const dateInput = screen.getByLabelText('Historial a fecha')
    fireEvent.change(dateInput, { target: { value: '2020-01-01' } })

    expect(screen.queryByText('Registrar hallazgo')).not.toBeInTheDocument()
    expect(screen.getByText(/Solo lectura/)).toBeInTheDocument()
  })
})
