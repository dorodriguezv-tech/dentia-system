import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ClinicalDocumentsSection } from './ClinicalDocumentsSection'
import * as api from './api'

vi.mock('./api')
vi.mock('../encounters/api')
vi.mock('../records/api')
vi.mock('../treatment/api')
import * as encountersApi from '../encounters/api'
import * as recordsApi from '../records/api'
import * as treatmentApi from '../treatment/api'

function renderSection(canWrite = true) {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <ClinicalDocumentsSection patientId="pat-1" canWrite={canWrite} />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.mocked(api.listPrescriptions).mockReset().mockResolvedValue([])
  vi.mocked(api.listReferralNotes).mockReset().mockResolvedValue([])
  vi.mocked(api.listCounterReferralNotes).mockReset().mockResolvedValue([])
  vi.mocked(api.createPrescription).mockReset()
  vi.mocked(api.getPrescriptionPdfBlobUrl).mockReset().mockResolvedValue('blob:prescription')
  vi.mocked(api.getPatientTreatmentsPerformedPdfBlobUrl)
    .mockReset()
    .mockResolvedValue('blob:performed')
  vi.mocked(encountersApi.listPatientEncounters).mockReset().mockResolvedValue([
    {
      id: 'enc-1',
      patient_id: 'pat-1',
      professional_id: 'prof-1',
      appointment_id: null,
      started_at: new Date().toISOString(),
      ended_at: null,
      chief_complaint: 'Dolor',
    },
  ])
  vi.mocked(encountersApi.getPatientTimeline).mockReset().mockResolvedValue([])
  vi.mocked(recordsApi.listAllergies).mockReset().mockResolvedValue([])
  vi.mocked(recordsApi.listVitalSigns).mockReset().mockResolvedValue([])
  vi.mocked(recordsApi.listMedications).mockReset().mockResolvedValue([])
  vi.mocked(treatmentApi.listPerformed).mockReset().mockResolvedValue([])
})

describe('ClinicalDocumentsSection', () => {
  it('muestra un mensaje claro cuando el paciente no tiene notas de evolucion', async () => {
    renderSection()
    expect(
      await screen.findByText('Este paciente todavia no tiene ninguna nota de evolucion capturada.'),
    ).toBeInTheDocument()
  })

  it('siempre muestra el boton de la ficha de tratamientos realizados, sin formulario', async () => {
    renderSection(false)
    expect(await screen.findByText('Ficha de tratamientos realizados')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Imprimir / Generar PDF' }),
    ).toBeInTheDocument()
  })

  it('oculta los formularios de captura sin permiso de escritura', async () => {
    renderSection(false)
    await screen.findByText('Ficha de tratamientos realizados')
    expect(screen.queryByPlaceholderText('Diagnostico')).not.toBeInTheDocument()
    expect(screen.queryByPlaceholderText('Motivo de interconsulta')).not.toBeInTheDocument()
  })

  it('crea una receta con un medicamento y abre el PDF', async () => {
    vi.mocked(api.createPrescription).mockResolvedValue({
      id: 'rx-1',
      patient_id: 'pat-1',
      encounter_id: 'enc-1',
      folio: 'RX-000001',
      diagnostico: 'Caries',
      medications: [{ nombre: 'Amoxicilina', detalle: 'Cada 8 horas' }],
      is_active: true,
      annul_reason: null,
      created_at: new Date().toISOString(),
    })
    renderSection()

    await screen.findByText('Sin recetas generadas.')
    const prescriptionCard = screen.getByText('Receta').closest('details') as HTMLElement
    await userEvent.type(within(prescriptionCard).getByPlaceholderText('Diagnostico'), 'Caries')
    await userEvent.type(within(prescriptionCard).getByPlaceholderText('Medicamento'), 'Amoxicilina')
    await userEvent.type(
      within(prescriptionCard).getByPlaceholderText(
        'Forma farmaceutica, dosis, frecuencia, via, duracion e indicaciones',
      ),
      'Cada 8 horas',
    )
    await userEvent.click(
      within(prescriptionCard).getByRole('button', { name: 'Imprimir / Generar PDF' }),
    )

    await waitFor(() => expect(api.createPrescription).toHaveBeenCalled())
    expect(api.createPrescription).toHaveBeenCalledWith('pat-1', {
      encounter_id: 'enc-1',
      diagnostico: 'Caries',
      medications: [{ nombre: 'Amoxicilina', detalle: 'Cada 8 horas' }],
    })
  })
})
