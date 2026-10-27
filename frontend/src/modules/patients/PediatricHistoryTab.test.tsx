import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '../auth/store'
import { useEncounterPicker } from '../encounters/useEncounterPicker'
import { PediatricHistoryTab } from './PediatricHistoryTab'

vi.mock('../encounters/api')
vi.mock('../catalogs/api')
vi.mock('../odontogram/api')
vi.mock('../odontologicalHistory/api')
vi.mock('../pediatricHistory/api')

import * as catalogsApi from '../catalogs/api'
import * as encountersApi from '../encounters/api'
import * as odontoApi from '../odontologicalHistory/api'
import * as odontogramApi from '../odontogram/api'
import * as pedApi from '../pediatricHistory/api'

/** Harness minimo: PediatricHistoryTab recibe el EncounterPicker ya
 * construido (igual que ExpedienteTab.tsx / OdontologicalHistoryTab.test.tsx),
 * asi que las pruebas lo obtienen del mismo hook real en vez de simular su
 * forma a mano. */
function Harness({ canWrite = true }: { canWrite?: boolean }) {
  const encounterPicker = useEncounterPicker('pat-1', canWrite, true)
  return <PediatricHistoryTab patientId="pat-1" canWrite={canWrite} encounterPicker={encounterPicker} />
}

function renderTab(canWrite = true) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <Harness canWrite={canWrite} />
    </QueryClientProvider>,
  )
}

function catalogItem(catalogType: string, code: string, name: string): import('../catalogs/types').CatalogItemOut {
  return {
    id: `${catalogType}-${code}`,
    catalog_type: catalogType,
    code,
    name,
    is_active: true,
    sort_order: 0,
    extra: {},
    updated_at: new Date().toISOString(),
  }
}

describe('PediatricHistoryTab', () => {
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

    vi.mocked(encountersApi.listPatientEncounters).mockReset().mockResolvedValue([
      {
        id: 'enc-hoy',
        patient_id: 'pat-1',
        professional_id: 'prof-1',
        appointment_id: null,
        chief_complaint: 'Revision',
        started_at: new Date().toISOString(),
        ended_at: null,
      },
    ])

    vi.mocked(catalogsApi.listCatalogItems).mockReset().mockImplementation(async (catalogType) => {
      if (catalogType === 'pediatric_tooth_anomaly') {
        return [
          catalogItem('pediatric_tooth_anomaly', 'hipoplasia', 'Hipoplasia (Hip)'),
          catalogItem('pediatric_tooth_anomaly', 'ausente_congenito', 'Ausente (congenito)'),
        ]
      }
      return []
    })

    vi.mocked(odontogramApi.getOdontogram).mockReset().mockResolvedValue([])

    vi.mocked(odontoApi.listToothTreatmentPlanEntries).mockReset().mockResolvedValue([])
    vi.mocked(odontoApi.createToothTreatmentPlanEntry).mockReset()
    vi.mocked(odontoApi.annulToothTreatmentPlanEntry).mockReset()

    vi.mocked(pedApi.listPerinatalHistories).mockReset().mockResolvedValue([])
    vi.mocked(pedApi.createPerinatalHistory).mockReset()
    vi.mocked(pedApi.annulPerinatalHistory).mockReset()
    vi.mocked(pedApi.listOralHabits).mockReset().mockResolvedValue([])
    vi.mocked(pedApi.createOralHabits).mockReset()
    vi.mocked(pedApi.annulOralHabits).mockReset()
    vi.mocked(pedApi.listBehaviorMaturities).mockReset().mockResolvedValue([])
    vi.mocked(pedApi.createBehaviorMaturity).mockReset()
    vi.mocked(pedApi.annulBehaviorMaturity).mockReset()
    vi.mocked(pedApi.listOcclusions).mockReset().mockResolvedValue([])
    vi.mocked(pedApi.createOcclusion).mockReset()
    vi.mocked(pedApi.annulOcclusion).mockReset()
    vi.mocked(pedApi.listEruptionDentitions).mockReset().mockResolvedValue([])
    vi.mocked(pedApi.createEruptionDentition).mockReset()
    vi.mocked(pedApi.annulEruptionDentition).mockReset()
    vi.mocked(pedApi.listToothAnnotations).mockReset().mockResolvedValue([])
    vi.mocked(pedApi.createToothAnnotation).mockReset()
    vi.mocked(pedApi.annulToothAnnotation).mockReset()
    vi.mocked(pedApi.getPediatricHistoryPdfBlobUrl).mockReset()
  })

  it('muestra todas las secciones, con el odontograma pediatrico abierto y sin badge', async () => {
    renderTab()

    expect(
      await screen.findByText('Odontograma pediátrico (dentición mixta) y anotaciones por pieza'),
    ).toBeInTheDocument()
    expect(screen.getByText('Antecedentes perinatales y primer año de vida')).toBeInTheDocument()
    expect(screen.getByText('Hábitos y antecedentes bucales')).toBeInTheDocument()
    expect(screen.getByText('Madurez y conducta')).toBeInTheDocument()
    expect(screen.getByText('Oclusión y alineamiento')).toBeInTheDocument()
    expect(screen.getByText('Erupción y dentición')).toBeInTheDocument()
    expect(screen.getByText('Plan de tratamiento por órgano dental (pediátrico)')).toBeInTheDocument()

    // La seccion ancla (odontograma) nunca lleva el badge "Faltan datos".
    expect(
      screen.getByText('Odontograma pediátrico (dentición mixta) y anotaciones por pieza').textContent,
    ).not.toContain('Faltan datos')
    // Las demas secciones, sin datos por defecto, si lo muestran.
    expect((await screen.findAllByText('Faltan datos')).length).toBeGreaterThan(0)
  })

  it('solo la seccion del odontograma pediatrico muestra el selector de atencion', async () => {
    renderTab()
    await screen.findByText('Antecedentes perinatales y primer año de vida')
    expect(await screen.findAllByLabelText('Atencion')).toHaveLength(1)
  })

  it('habitos bucales: usa 3 radios (sin responder/si/no) en vez de checkboxes simples', async () => {
    renderTab()
    await screen.findByText('Hábitos y antecedentes bucales')

    const siOptions = screen.getAllByRole('radio', { name: 'Sí' })
    expect(siOptions.length).toBeGreaterThan(0)
    const sinResponder = screen.getAllByRole('radio', { name: 'Sin responder' })[0]
    expect(sinResponder).toBeChecked()
  })

  it('captura antecedentes perinatales con una respuesta "No"', async () => {
    vi.mocked(pedApi.createPerinatalHistory).mockResolvedValue({ id: 'perinatal-1' } as never)

    renderTab()
    const heading = await screen.findByText('Antecedentes perinatales y primer año de vida')
    const section = heading.closest('details') as HTMLElement

    await userEvent.click(within(section).getAllByRole('radio', { name: 'No' })[0])
    await userEvent.click(
      within(section).getByRole('button', { name: 'Guardar antecedentes perinatales' }),
    )

    await waitFor(() =>
      expect(pedApi.createPerinatalHistory).toHaveBeenCalledWith(
        'pat-1',
        expect.objectContaining({ encounter_id: 'enc-hoy' }),
      ),
    )
  })

  it('anota una pieza y la lista muestra la anomalia capturada', async () => {
    vi.mocked(pedApi.createToothAnnotation).mockResolvedValue({
      id: 'ann-1',
      encounter_id: 'enc-hoy',
      tooth_fdi: '55',
      anomaly_code: 'hipoplasia',
      hipoplasia_detail: null,
      is_active: true,
      origin: 'MANUAL',
      created_at: new Date().toISOString(),
    })

    renderTab()
    await screen.findByText('Odontograma pediátrico (dentición mixta) y anotaciones por pieza')

    await userEvent.selectOptions(screen.getByLabelText('Pieza FDI a anotar'), '55')
    await userEvent.selectOptions(screen.getByLabelText('Anomalía'), 'hipoplasia')
    await userEvent.click(screen.getByRole('button', { name: 'Anotar' }))

    await waitFor(() =>
      expect(pedApi.createToothAnnotation).toHaveBeenCalledWith(
        'pat-1',
        expect.objectContaining({ encounter_id: 'enc-hoy', tooth_fdi: '55', anomaly_code: 'hipoplasia' }),
      ),
    )
  })

  it('boton de PDF abre una pestana nueva y navega a la URL del blob', async () => {
    vi.mocked(pedApi.getPediatricHistoryPdfBlobUrl).mockResolvedValue('blob:mock-pdf')
    const openSpy = vi.spyOn(window, 'open').mockReturnValue({ location: { href: '' } } as never)

    renderTab()
    await userEvent.click(screen.getByRole('button', { name: 'Imprimir / Generar PDF' }))

    await waitFor(() => expect(pedApi.getPediatricHistoryPdfBlobUrl).toHaveBeenCalledWith('pat-1'))
    expect(openSpy).toHaveBeenCalled()
    openSpy.mockRestore()
  })

  it('sin permiso de escritura, no se muestran los formularios de captura', async () => {
    renderTab(false)
    await screen.findByText('Antecedentes perinatales y primer año de vida')
    expect(
      screen.queryByRole('button', { name: 'Guardar antecedentes perinatales' }),
    ).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Anotar' })).not.toBeInTheDocument()
  })
})
