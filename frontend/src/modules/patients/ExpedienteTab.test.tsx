import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '../auth/store'
import { ExpedienteTab } from './ExpedienteTab'

vi.mock('../encounters/api')
vi.mock('../records/api')
vi.mock('../diagnosis/api')
import * as diagnosisApi from '../diagnosis/api'
import * as encountersApi from '../encounters/api'
import * as recordsApi from '../records/api'

function renderExpediente() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <ExpedienteTab patientId="pat-1" />
    </QueryClientProvider>,
  )
}

describe('ExpedienteTab', () => {
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

    vi.mocked(recordsApi.listHistory).mockReset().mockResolvedValue([])
    vi.mocked(recordsApi.listAllergies).mockReset().mockResolvedValue([])
    vi.mocked(recordsApi.listMedications).mockReset().mockResolvedValue([])
    vi.mocked(recordsApi.listVitalSigns).mockReset().mockResolvedValue([])
    vi.mocked(diagnosisApi.listDiagnoses).mockReset().mockResolvedValue([])
    vi.mocked(recordsApi.createAllergy).mockReset()
  })

  it('A3/A4: sin atenciones, el selector ofrece iniciar una y el boton de Agregar '
    + 'alergia funciona en dos clics', async () => {
    vi.mocked(encountersApi.listPatientEncounters).mockReset().mockResolvedValue([])
    vi.mocked(encountersApi.createEncounter).mockReset().mockResolvedValue({
      id: 'enc-nueva',
      patient_id: 'pat-1',
      professional_id: 'prof-1',
      appointment_id: null,
      chief_complaint: null,
      started_at: new Date().toISOString(),
      ended_at: null,
    })
    vi.mocked(recordsApi.createAllergy).mockResolvedValue({
      id: 'allergy-1',
      encounter_id: 'enc-nueva',
      substance: 'Penicilina',
      reaction: null,
      severity: 'leve',
      is_active: true,
      created_at: new Date().toISOString(),
    })

    renderExpediente()

    const selects = await screen.findAllByLabelText('Atencion')
    // Antes de la correccion A3, aqui solo existia "Selecciona una atencion..." y el
    // boton de Agregar se quedaba deshabilitado para siempre en un paciente sin
    // atenciones (A4). Ahora el selector siempre ofrece una salida.
    const allergySelect = selects[1] as HTMLSelectElement
    expect(
      Array.from(allergySelect.options).some((o) => o.textContent?.includes('Iniciar atencion nueva')),
    ).toBe(true)

    // Clic 1: iniciar la atencion desde el selector de la seccion de Alergias.
    await userEvent.selectOptions(
      allergySelect,
      within(allergySelect).getByText('+ Iniciar atencion nueva'),
    )
    await waitFor(() => expect(encountersApi.createEncounter).toHaveBeenCalledWith({ patient_id: 'pat-1' }))

    await userEvent.type(screen.getByPlaceholderText('Sustancia'), 'Penicilina')

    const addAllergyButton = screen.getByRole('button', { name: 'Agregar alergia' })
    await waitFor(() => expect(addAllergyButton).not.toBeDisabled())

    // Clic 2: Agregar alergia.
    await userEvent.click(addAllergyButton)
    await waitFor(() =>
      expect(recordsApi.createAllergy).toHaveBeenCalledWith('pat-1', {
        encounter_id: 'enc-nueva',
        substance: 'Penicilina',
        reaction: null,
        severity: 'leve',
      }),
    )
  })

  it('A3: si ya hay una atencion de hoy, se preselecciona sola', async () => {
    const todayIso = new Date().toISOString()
    vi.mocked(encountersApi.listPatientEncounters).mockReset().mockResolvedValue([
      {
        id: 'enc-hoy',
        patient_id: 'pat-1',
        professional_id: 'prof-1',
        appointment_id: null,
        chief_complaint: 'Dolor',
        started_at: todayIso,
        ended_at: null,
      },
    ])

    renderExpediente()

    const selects = await screen.findAllByLabelText('Atencion')
    await waitFor(() => expect((selects[0] as HTMLSelectElement).value).toBe('enc-hoy'))
  })

  it('A3: si la carga de atenciones falla, se muestra el error (no un selector vacio en silencio)', async () => {
    vi.mocked(encountersApi.listPatientEncounters).mockReset().mockRejectedValue(new Error('500'))

    renderExpediente()

    expect(
      await screen.findAllByText('No se pudieron cargar las atenciones del paciente.'),
    ).not.toHaveLength(0)
  })
})
