import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '../auth/store'
import { useEncounterPicker } from '../encounters/useEncounterPicker'
import { OdontologicalHistoryTab } from './OdontologicalHistoryTab'

vi.mock('../encounters/api')
vi.mock('../catalogs/api')
vi.mock('../records/api')
vi.mock('../odontogram/api')
vi.mock('../odontologicalHistory/api')
vi.mock('../periodontogram/api')

import * as catalogsApi from '../catalogs/api'
import * as encountersApi from '../encounters/api'
import * as odontoApi from '../odontologicalHistory/api'
import * as odontogramApi from '../odontogram/api'
import * as periodontogramApi from '../periodontogram/api'
import * as recordsApi from '../records/api'

/** Harness minimo: OdontologicalHistoryTab recibe el EncounterPicker ya
 * construido (igual que ExpedienteTab.tsx), asi que las pruebas lo obtienen
 * del mismo hook real en vez de simular su forma a mano. */
function Harness({ canWrite = true }: { canWrite?: boolean }) {
  const encounterPicker = useEncounterPicker('pat-1', canWrite, true)
  return (
    <OdontologicalHistoryTab patientId="pat-1" canWrite={canWrite} encounterPicker={encounterPicker} />
  )
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

describe('OdontologicalHistoryTab', () => {
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
        chief_complaint: 'Dolor',
        started_at: new Date().toISOString(),
        ended_at: null,
      },
    ])

    vi.mocked(catalogsApi.listCatalogItems).mockReset().mockResolvedValue([])
    vi.mocked(recordsApi.listAllergies).mockReset().mockResolvedValue([])
    vi.mocked(recordsApi.listMedications).mockReset().mockResolvedValue([])
    vi.mocked(recordsApi.listNonPathologicalHistory).mockReset().mockResolvedValue([])

    vi.mocked(odontogramApi.getOdontogram).mockReset().mockResolvedValue([])

    vi.mocked(odontoApi.listOdontologicalExams).mockReset().mockResolvedValue([])
    vi.mocked(odontoApi.createOdontologicalExam).mockReset()
    vi.mocked(odontoApi.annulOdontologicalExam).mockReset()
    vi.mocked(odontoApi.listPeriodontalAnamneses).mockReset().mockResolvedValue([])
    vi.mocked(odontoApi.createPeriodontalAnamnesis).mockReset()
    vi.mocked(odontoApi.annulPeriodontalAnamnesis).mockReset()
    vi.mocked(odontoApi.listRadiographicAnalyses).mockReset().mockResolvedValue([])
    vi.mocked(odontoApi.createRadiographicAnalysis).mockReset()
    vi.mocked(odontoApi.annulRadiographicAnalysis).mockReset()
    vi.mocked(odontoApi.listOdontogramDiagnosisDetails).mockReset().mockResolvedValue([])
    vi.mocked(odontoApi.createOdontogramDiagnosisDetail).mockReset()
    vi.mocked(odontoApi.annulOdontogramDiagnosisDetail).mockReset()
    vi.mocked(odontoApi.listParallelometerAnalyses).mockReset().mockResolvedValue([])
    vi.mocked(odontoApi.createParallelometerAnalysis).mockReset()
    vi.mocked(odontoApi.annulParallelometerAnalysis).mockReset()
    vi.mocked(odontoApi.listRemovablePartialDentureDesigns).mockReset().mockResolvedValue([])
    vi.mocked(odontoApi.createRemovablePartialDentureDesign).mockReset()
    vi.mocked(odontoApi.annulRemovablePartialDentureDesign).mockReset()
    vi.mocked(odontoApi.listToothDiagnosisEntries).mockReset().mockResolvedValue([])
    vi.mocked(odontoApi.createToothDiagnosisEntry).mockReset()
    vi.mocked(odontoApi.annulToothDiagnosisEntry).mockReset()
    vi.mocked(odontoApi.listToothTreatmentPlanEntries).mockReset().mockResolvedValue([])
    vi.mocked(odontoApi.createToothTreatmentPlanEntry).mockReset()
    vi.mocked(odontoApi.annulToothTreatmentPlanEntry).mockReset()
    vi.mocked(odontoApi.getOdontologicalHistoryPdfBlobUrl).mockReset()

    vi.mocked(periodontogramApi.listProbingSites).mockReset().mockResolvedValue([])
    vi.mocked(periodontogramApi.createProbingSite).mockReset()
    vi.mocked(periodontogramApi.annulProbingSite).mockReset()
    vi.mocked(periodontogramApi.listToothMeasurements).mockReset().mockResolvedValue([])
    vi.mocked(periodontogramApi.createToothMeasurement).mockReset()
    vi.mocked(periodontogramApi.annulToothMeasurement).mockReset()
    vi.mocked(periodontogramApi.listIndexEntries).mockReset().mockResolvedValue([])
    vi.mocked(periodontogramApi.createIndexEntry).mockReset()
    vi.mocked(periodontogramApi.annulIndexEntry).mockReset()
    vi.mocked(periodontogramApi.getIndicesSummary).mockReset().mockResolvedValue({
      encounter_id: null,
      placa: { numero_caras_totales: 0, numero_caras_pigmentadas: 0, indice_placa_dentobacteriana: null },
      gingival: { numero_sitios_totales: 0, indice_gingival_total: null },
    })
    vi.mocked(periodontogramApi.listOcclusalContacts).mockReset().mockResolvedValue([])
    vi.mocked(periodontogramApi.createOcclusalContact).mockReset()
    vi.mocked(periodontogramApi.annulOcclusalContact).mockReset()
    vi.mocked(periodontogramApi.listObservations).mockReset().mockResolvedValue([])
    vi.mocked(periodontogramApi.createObservation).mockReset()
    vi.mocked(periodontogramApi.annulObservation).mockReset()
    vi.mocked(periodontogramApi.getPeriodontogramPdfBlobUrl).mockReset()
  })

  it('muestra todas las secciones, con el Odontograma de diagnostico abierto y sin badge', async () => {
    renderTab()

    expect(await screen.findByText('Exploración cabeza y cuello, ATM y tejidos blandos')).toBeInTheDocument()
    expect(screen.getByText('Anamnesis periodontal')).toBeInTheDocument()
    expect(screen.getByText('Análisis radiográfico')).toBeInTheDocument()
    expect(screen.getByText('Odontograma de diagnóstico')).toBeInTheDocument()
    expect(screen.getByText('Periodontograma completo')).toBeInTheDocument()
    expect(screen.getByText('Análisis con paralelómetro')).toBeInTheDocument()
    expect(screen.getByText('Diseño de prótesis parcial removible')).toBeInTheDocument()
    expect(screen.getByText('Diagnóstico por órgano dental')).toBeInTheDocument()
    expect(screen.getByText('Plan de tratamiento por órgano dental')).toBeInTheDocument()

    // La seccion ancla (Odontograma) nunca lleva el badge "Faltan datos".
    expect(screen.getByText('Odontograma de diagnóstico').textContent).not.toContain('Faltan datos')
    // Las demas secciones, sin datos por defecto, si lo muestran.
    expect((await screen.findAllByText('Faltan datos')).length).toBeGreaterThan(0)
  })

  it('solo la seccion del Odontograma de diagnostico muestra el selector de atencion', async () => {
    renderTab()
    await screen.findByText('Exploración cabeza y cuello, ATM y tejidos blandos')
    expect(await screen.findAllByLabelText('Atencion')).toHaveLength(1)
  })

  it('exploracion ATM: "Ninguno" es mutuamente excluyente con los hallazgos de ATM', async () => {
    renderTab()
    await screen.findByText('Exploración cabeza y cuello, ATM y tejidos blandos')

    const ninguno = screen.getByRole('checkbox', { name: 'Ninguno' })
    const chasquidos = screen.getByRole('checkbox', { name: 'Chasquidos (derecho)' })

    await userEvent.click(ninguno)
    expect(ninguno).toBeChecked()

    await userEvent.click(chasquidos)
    expect(ninguno).not.toBeChecked()
    expect(chasquidos).toBeChecked()
  })

  it('captura la exploracion odontologica (ATM + guardar)', async () => {
    vi.mocked(odontoApi.createOdontologicalExam).mockResolvedValue({
      id: 'exam-1',
      encounter_id: 'enc-hoy',
    } as never)

    renderTab()
    await userEvent.click(await screen.findByRole('checkbox', { name: 'Chasquidos (derecho)' }))
    await userEvent.click(screen.getByRole('button', { name: 'Guardar exploración' }))

    await waitFor(() =>
      expect(odontoApi.createOdontologicalExam).toHaveBeenCalledWith(
        'pat-1',
        expect.objectContaining({ encounter_id: 'enc-hoy', chasquidos_derecho: true }),
      ),
    )
  })

  it('anamnesis periodontal: muestra el contexto de tabaco/alcohol ya capturado y responde una pregunta', async () => {
    vi.mocked(catalogsApi.listCatalogItems).mockImplementation(async (catalogType) => {
      if (catalogType === 'periodontal_anamnesis_question') {
        return [catalogItem('periodontal_anamnesis_question', 'fuma', '¿Fuma?')]
      }
      return []
    })
    vi.mocked(recordsApi.listNonPathologicalHistory).mockResolvedValue([
      {
        id: 'nonpath-1',
        encounter_id: 'enc-hoy',
        comidas_dia: null,
        calidad_alimentacion: null,
        agua_litros_dia: null,
        trastornos_sueno: false,
        trastornos_sueno_texto: null,
        cepillados_dia: null,
        hilo_dental: false,
        enjuague_bucal: false,
        deportes: false,
        deportes_cual: null,
        derechohabiencia: null,
        estado_civil: null,
        medicamentos_suplementos: false,
        medicamentos_controlados: false,
        medicamentos_texto: null,
        servicios_basicos: {},
        adicciones: { tabaco: { has: true, detail: '5 cigarros/dia' } },
        is_active: true,
        origin: 'MANUAL',
        created_at: new Date().toISOString(),
      },
    ])
    vi.mocked(odontoApi.createPeriodontalAnamnesis).mockResolvedValue({ id: 'pa-1' } as never)

    renderTab()

    expect(
      await screen.findByText(
        'Ya capturado en Historia Clínica General: Tabaco Sí (5 cigarros/dia).',
      ),
    ).toBeInTheDocument()

    await userEvent.click(screen.getByRole('radio', { name: 'Sí' }))
    await userEvent.click(screen.getByRole('button', { name: 'Guardar anamnesis periodontal' }))

    await waitFor(() =>
      expect(odontoApi.createPeriodontalAnamnesis).toHaveBeenCalledWith(
        'pat-1',
        expect.objectContaining({ encounter_id: 'enc-hoy', answers: { fuma: 'si' } }),
      ),
    )
  })

  it('odontograma de diagnostico: guarda Kennedy y una fila de protesis fija', async () => {
    vi.mocked(odontoApi.createOdontogramDiagnosisDetail).mockResolvedValue({ id: 'odd-1' } as never)

    renderTab()
    const heading = await screen.findByText('Odontograma de diagnóstico')
    const section = heading.closest('details') as HTMLElement

    await userEvent.selectOptions(screen.getByLabelText('Kennedy superior'), 'I')
    await userEvent.click(within(section).getByRole('button', { name: '+ Agregar fila' }))
    await userEvent.type(screen.getByLabelText('Pieza FDI (fila 1)'), '16')
    await userEvent.type(screen.getByLabelText('Relación corona-raíz (fila 1)'), '1:1')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar datos complementarios' }))

    await waitFor(() =>
      expect(odontoApi.createOdontogramDiagnosisDetail).toHaveBeenCalledWith(
        'pat-1',
        expect.objectContaining({
          encounter_id: 'enc-hoy',
          kennedy_sup_class: 'I',
          fixed_prosthesis_analysis: [{ tooth_fdi: '16', cr_relation: '1:1' }],
        }),
      ),
    )
  })

  it('diagnostico por organo dental: captura una pieza y guarda', async () => {
    vi.mocked(odontoApi.createToothDiagnosisEntry).mockResolvedValue({ id: 'td-1' } as never)

    renderTab()
    await userEvent.type(await screen.findByLabelText('Diagnóstico pieza 11'), 'Caries oclusal')
    await userEvent.click(
      screen.getByRole('button', { name: 'Guardar diagnóstico por órgano dental' }),
    )

    await waitFor(() =>
      expect(odontoApi.createToothDiagnosisEntry).toHaveBeenCalledWith(
        'pat-1',
        expect.objectContaining({ encounter_id: 'enc-hoy', diagnoses: { '11': 'Caries oclusal' } }),
      ),
    )
  })

  it('boton de PDF abre una pestana nueva y navega a la URL del blob', async () => {
    vi.mocked(odontoApi.getOdontologicalHistoryPdfBlobUrl).mockResolvedValue('blob:mock-pdf')
    const openSpy = vi.spyOn(window, 'open').mockReturnValue({ location: { href: '' } } as never)

    renderTab()
    // Hay 2 botones con este texto: el de toda la Historia Odontologica (el
    // primero, fuera de cualquier seccion) y el del Periodontograma completo
    // (al final de esa seccion nueva, Fase G) -- se prueba el primero aqui.
    await userEvent.click(screen.getAllByRole('button', { name: 'Imprimir / Generar PDF' })[0])

    await waitFor(() => expect(odontoApi.getOdontologicalHistoryPdfBlobUrl).toHaveBeenCalledWith('pat-1'))
    expect(openSpy).toHaveBeenCalled()
    openSpy.mockRestore()
  })

  it('sin permiso de escritura, no se muestran los formularios de captura', async () => {
    renderTab(false)
    await screen.findByText('Exploración cabeza y cuello, ATM y tejidos blandos')
    expect(screen.queryByRole('button', { name: 'Guardar exploración' })).not.toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Guardar datos complementarios' }),
    ).not.toBeInTheDocument()
  })
})
