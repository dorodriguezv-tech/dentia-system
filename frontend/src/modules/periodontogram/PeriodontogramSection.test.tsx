import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { PeriodontogramSection } from './PeriodontogramSection'

vi.mock('./api')

import * as api from './api'

function renderSection(canWrite = true, encounterId = 'enc-hoy') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <PeriodontogramSection patientId="pat-1" canWrite={canWrite} encounterId={encounterId} />
    </QueryClientProvider>,
  )
  return queryClient
}

describe('PeriodontogramSection', () => {
  beforeEach(() => {
    vi.mocked(api.listProbingSites).mockReset().mockResolvedValue([])
    vi.mocked(api.createProbingSite).mockReset()
    vi.mocked(api.annulProbingSite).mockReset()
    vi.mocked(api.listToothMeasurements).mockReset().mockResolvedValue([])
    vi.mocked(api.createToothMeasurement).mockReset()
    vi.mocked(api.annulToothMeasurement).mockReset()
    vi.mocked(api.listIndexEntries).mockReset().mockResolvedValue([])
    vi.mocked(api.createIndexEntry).mockReset()
    vi.mocked(api.annulIndexEntry).mockReset()
    vi.mocked(api.getIndicesSummary).mockReset().mockResolvedValue({
      encounter_id: null,
      placa: { numero_caras_totales: 0, numero_caras_pigmentadas: 0, indice_placa_dentobacteriana: null },
      gingival: { numero_sitios_totales: 0, indice_gingival_total: null },
    })
    vi.mocked(api.listOcclusalContacts).mockReset().mockResolvedValue([])
    vi.mocked(api.createOcclusalContact).mockReset()
    vi.mocked(api.annulOcclusalContact).mockReset()
    vi.mocked(api.listObservations).mockReset().mockResolvedValue([])
    vi.mocked(api.createObservation).mockReset()
    vi.mocked(api.annulObservation).mockReset()
    vi.mocked(api.getPeriodontogramPdfBlobUrl).mockReset()
  })

  it('muestra todas las subsecciones y el badge de datos faltantes', async () => {
    renderSection()

    expect(await screen.findByText('Periodontograma completo')).toBeInTheDocument()
    expect(screen.getByText('Sondeo periodontal')).toBeInTheDocument()
    expect(screen.getByText('Movilidad (Miller) y furcación por pieza')).toBeInTheDocument()
    expect(screen.getByText('Índice de placa dentobacteriana')).toBeInTheDocument()
    expect(screen.getByText('Índice gingival')).toBeInTheDocument()
    expect(screen.getByText('Tablas de oclusión')).toBeInTheDocument()
    expect(screen.getByText('Observaciones del periodontograma')).toBeInTheDocument()
    expect((await screen.findAllByText('Faltan datos')).length).toBeGreaterThan(0)
  })

  it('sondeo periodontal: abre el panel de un sitio, captura y guarda', async () => {
    vi.mocked(api.createProbingSite).mockResolvedValue({
      id: 'probe-1',
      encounter_id: 'enc-hoy',
      tooth_fdi: '11',
      site: 'vestibular',
      probing_depth_mm: 3,
      recession_mm: 1,
      bleeding_on_probing: true,
      suppuration: false,
      clinical_attachment_level_mm: 4,
      is_active: true,
      origin: 'MANUAL',
      created_at: new Date().toISOString(),
    })

    renderSection()
    await screen.findByText('Sondeo periodontal')

    const siteButtons = screen.getAllByTitle('Pieza 11: Vestibular')
    await userEvent.click(siteButtons[0])

    await userEvent.type(screen.getByLabelText('Profundidad de sondaje pieza 11 Vestibular'), '3')
    await userEvent.type(screen.getByLabelText('Recesión pieza 11 Vestibular'), '1')
    await userEvent.click(screen.getByRole('checkbox', { name: 'Sangrado al sondaje' }))
    await userEvent.click(screen.getByRole('button', { name: 'Guardar sondeo' }))

    await waitFor(() =>
      expect(api.createProbingSite).toHaveBeenCalledWith('pat-1', {
        encounter_id: 'enc-hoy',
        tooth_fdi: '11',
        site: 'vestibular',
        probing_depth_mm: 3,
        recession_mm: 1,
        bleeding_on_probing: true,
        suppuration: false,
      }),
    )
  })

  it('movilidad/furcacion: selecciona un grado de movilidad y guarda la pieza', async () => {
    vi.mocked(api.createToothMeasurement).mockResolvedValue({
      id: 'meas-1',
      encounter_id: 'enc-hoy',
      tooth_fdi: '11',
      mobility_grade: 2,
      furcation_grade: null,
      is_active: true,
      origin: 'MANUAL',
      created_at: new Date().toISOString(),
    })

    renderSection()
    await screen.findByText('Movilidad (Miller) y furcación por pieza')

    await userEvent.selectOptions(screen.getByLabelText('Movilidad pieza 11'), '2')

    await waitFor(() =>
      expect(api.createToothMeasurement).toHaveBeenCalledWith('pat-1', {
        encounter_id: 'enc-hoy',
        tooth_fdi: '11',
        mobility_grade: 2,
        furcation_grade: null,
      }),
    )
  })

  it('indice de placa: captura un grado, muestra el resumen y limpiar una celda la anula', async () => {
    vi.mocked(api.createIndexEntry).mockResolvedValue({
      id: 'idx-1',
      encounter_id: 'enc-hoy',
      tooth_fdi: '11',
      index_type: 'placa',
      surface: 'vestibular',
      grade: 1,
      is_active: true,
      origin: 'MANUAL',
      created_at: new Date().toISOString(),
    })
    vi.mocked(api.getIndicesSummary).mockResolvedValue({
      encounter_id: 'enc-hoy',
      placa: { numero_caras_totales: 1, numero_caras_pigmentadas: 1, indice_placa_dentobacteriana: 1 },
      gingival: { numero_sitios_totales: 0, indice_gingival_total: null },
    })

    renderSection()
    await screen.findByText('Índice de placa dentobacteriana')

    await userEvent.selectOptions(
      screen.getByLabelText('Índice de placa dentobacteriana Vestibular pieza 11'),
      '1',
    )

    await waitFor(() =>
      expect(api.createIndexEntry).toHaveBeenCalledWith('pat-1', {
        encounter_id: 'enc-hoy',
        tooth_fdi: '11',
        index_type: 'placa',
        surface: 'vestibular',
        grade: 1,
      }),
    )

    expect(await screen.findByText('Número de caras pigmentadas')).toBeInTheDocument()
  })

  it('tablas de oclusion: marcar una pieza crea el contacto', async () => {
    vi.mocked(api.createOcclusalContact).mockResolvedValue({
      id: 'occ-1',
      encounter_id: 'enc-hoy',
      tooth_fdi: '11',
      movement: 'centrica',
      is_active: true,
      origin: 'MANUAL',
      created_at: new Date().toISOString(),
    })

    renderSection()
    await screen.findByText('Tablas de oclusión')

    await userEvent.click(screen.getByLabelText('Oclusión céntrica pieza 11'))

    await waitFor(() =>
      expect(api.createOcclusalContact).toHaveBeenCalledWith('pat-1', {
        encounter_id: 'enc-hoy',
        tooth_fdi: '11',
        movement: 'centrica',
      }),
    )
  })

  it('tablas de oclusion: desmarcar una pieza ya activa anula el contacto sin pedir motivo', async () => {
    vi.mocked(api.listOcclusalContacts).mockResolvedValue([
      {
        id: 'occ-1',
        encounter_id: 'enc-hoy',
        tooth_fdi: '11',
        movement: 'centrica',
        is_active: true,
        origin: 'MANUAL',
        created_at: new Date().toISOString(),
      },
    ])

    renderSection()
    await screen.findByText('Tablas de oclusión')

    const checkbox = await screen.findByLabelText('Oclusión céntrica pieza 11')
    expect(checkbox).toBeChecked()
    await userEvent.click(checkbox)

    await waitFor(() =>
      expect(api.annulOcclusalContact).toHaveBeenCalledWith('pat-1', 'occ-1', 'Desmarcado'),
    )
  })

  it('observaciones: captura y guarda', async () => {
    vi.mocked(api.createObservation).mockResolvedValue({
      id: 'obs-1',
      encounter_id: 'enc-hoy',
      observaciones: 'Encia sana',
      is_active: true,
      origin: 'MANUAL',
      created_at: new Date().toISOString(),
    })

    renderSection()
    await screen.findByText('Observaciones del periodontograma')

    await userEvent.type(screen.getByPlaceholderText('Observaciones (opcional)'), 'Encia sana')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar observaciones' }))

    await waitFor(() =>
      expect(api.createObservation).toHaveBeenCalledWith('pat-1', {
        encounter_id: 'enc-hoy',
        observaciones: 'Encia sana',
      }),
    )
  })

  it('boton de PDF abre una pestana nueva y navega a la URL del blob', async () => {
    vi.mocked(api.getPeriodontogramPdfBlobUrl).mockResolvedValue('blob:mock-pdf')
    const openSpy = vi.spyOn(window, 'open').mockReturnValue({ location: { href: '' } } as never)

    renderSection()
    await userEvent.click(await screen.findByRole('button', { name: 'Imprimir / Generar PDF' }))

    await waitFor(() => expect(api.getPeriodontogramPdfBlobUrl).toHaveBeenCalledWith('pat-1'))
    expect(openSpy).toHaveBeenCalled()
    openSpy.mockRestore()
  })

  it('sin permiso de escritura, no se muestran controles de captura', async () => {
    renderSection(false)
    await screen.findByText('Sondeo periodontal')

    expect(screen.queryByRole('button', { name: 'Mesio' })).not.toBeInTheDocument()
    expect(screen.getAllByTitle('Pieza 11: Vestibular')[0].tagName).toBe('SPAN')
    expect(screen.queryByLabelText('Movilidad pieza 11')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Oclusión céntrica pieza 11')).not.toBeInTheDocument()
    expect(screen.queryByPlaceholderText('Observaciones (opcional)')).not.toBeInTheDocument()
  })
})
