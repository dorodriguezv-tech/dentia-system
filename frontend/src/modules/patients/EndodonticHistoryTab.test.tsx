import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '../auth/store'
import { useEncounterPicker } from '../encounters/useEncounterPicker'
import { EndodonticHistoryTab } from './EndodonticHistoryTab'

vi.mock('../encounters/api')
vi.mock('../endodonticHistory/api')

import * as encountersApi from '../encounters/api'
import * as endoApi from '../endodonticHistory/api'

/** Harness minimo: EndodonticHistoryTab recibe el EncounterPicker ya
 * construido (igual que OdontologicalHistoryTab.test.tsx /
 * PediatricHistoryTab.test.tsx), asi que las pruebas lo obtienen del mismo
 * hook real en vez de simular su forma a mano. */
function Harness({ canWrite = true }: { canWrite?: boolean }) {
  const encounterPicker = useEncounterPicker('pat-1', canWrite, true)
  return <EndodonticHistoryTab patientId="pat-1" canWrite={canWrite} encounterPicker={encounterPicker} />
}

function renderTab(canWrite = true) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <Harness canWrite={canWrite} />
    </QueryClientProvider>,
  )
}

describe('EndodonticHistoryTab', () => {
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

    vi.mocked(endoApi.listInterrogations).mockReset().mockResolvedValue([])
    vi.mocked(endoApi.createInterrogation).mockReset()
    vi.mocked(endoApi.annulInterrogation).mockReset()
    vi.mocked(endoApi.listPulpSensitivityTests).mockReset().mockResolvedValue([])
    vi.mocked(endoApi.createPulpSensitivityTest).mockReset()
    vi.mocked(endoApi.annulPulpSensitivityTest).mockReset()
    vi.mocked(endoApi.listPeriodontalTests).mockReset().mockResolvedValue([])
    vi.mocked(endoApi.createPeriodontalTest).mockReset()
    vi.mocked(endoApi.annulPeriodontalTest).mockReset()
    vi.mocked(endoApi.listRadiographicInterpretations).mockReset().mockResolvedValue([])
    vi.mocked(endoApi.createRadiographicInterpretation).mockReset()
    vi.mocked(endoApi.annulRadiographicInterpretation).mockReset()
    vi.mocked(endoApi.listDiagnosisTreatments).mockReset().mockResolvedValue([])
    vi.mocked(endoApi.createDiagnosisTreatment).mockReset()
    vi.mocked(endoApi.annulDiagnosisTreatment).mockReset()
    vi.mocked(endoApi.listToothDiagnosisCodes).mockReset().mockResolvedValue([])
    vi.mocked(endoApi.createToothDiagnosisCode).mockReset()
    vi.mocked(endoApi.annulToothDiagnosisCode).mockReset()
    vi.mocked(endoApi.listWorkingLengths).mockReset().mockResolvedValue([])
    vi.mocked(endoApi.createWorkingLength).mockReset()
    vi.mocked(endoApi.annulWorkingLength).mockReset()
    vi.mocked(endoApi.getEndodonticHistoryPdfBlobUrl).mockReset()
  })

  it('muestra todas las secciones, todas cerradas por defecto (ronda 2.1: sin excepcion ni para el ancla)', async () => {
    renderTab()

    expect(await screen.findByText('Interrogatorio')).toBeInTheDocument()
    expect(screen.getByText('Pruebas de sensibilidad pulpar')).toBeInTheDocument()
    expect(screen.getByText('Pruebas periodontales')).toBeInTheDocument()
    expect(screen.getByText('Interpretación radiográfica')).toBeInTheDocument()
    expect(screen.getByText('Diagnóstico y tratamiento')).toBeInTheDocument()
    expect(screen.getByText('Odontograma de diagnóstico y evolución (18 códigos)')).toBeInTheDocument()
    expect(screen.getByText('Longitud de trabajo')).toBeInTheDocument()

    // La seccion ancla (odontograma de 18 codigos) empieza cerrada -- ronda
    // 2.1, sin excepcion -- pero sigue siendo la unica con el selector de
    // atencion.
    expect(await screen.findAllByLabelText('Atencion')).toHaveLength(1)
  })

  it('captura el interrogatorio (checklist de antecedentes) y guarda', async () => {
    vi.mocked(endoApi.createInterrogation).mockResolvedValue({
      id: 'interr-1',
      encounter_id: 'enc-hoy',
    } as never)

    renderTab()
    await userEvent.click(await screen.findByRole('checkbox', { name: 'Caries' }))
    await userEvent.click(screen.getByRole('button', { name: 'Guardar interrogatorio' }))

    await waitFor(() =>
      expect(endoApi.createInterrogation).toHaveBeenCalledWith(
        'pat-1',
        expect.objectContaining({
          encounter_id: 'enc-hoy',
          antecedentes: { caries: true },
        }),
      ),
    )
    expect(endoApi.annulInterrogation).not.toHaveBeenCalled()
  })

  it('patron "editar" (ronda 2.2): con una entrada activa, el formulario se precarga y al '
    + 'guardar anula automaticamente la anterior antes de crear la nueva', async () => {
    vi.mocked(endoApi.listInterrogations).mockResolvedValue([
      {
        id: 'interr-1',
        encounter_id: 'enc-hoy',
        antecedentes: { caries: true },
        antecedentes_otro_detalle: null,
        dolor: {},
        dolor_otro_detalle: null,
        estimulo: {},
        estimulo_otro_detalle: null,
        examen_intrabucal: {},
        examen_intrabucal_otro_detalle: null,
        examen_extrabucal: {},
        examen_extrabucal_otro_detalle: null,
        is_active: true,
        origin: 'MANUAL',
        created_at: new Date().toISOString(),
      },
    ])
    vi.mocked(endoApi.annulInterrogation).mockResolvedValue({} as never)
    vi.mocked(endoApi.createInterrogation).mockResolvedValue({ id: 'interr-2' } as never)

    renderTab()

    const cariesCheckbox = (await screen.findByRole('checkbox', {
      name: 'Caries',
    })) as HTMLInputElement
    // Precargado desde la entrada activa.
    await waitFor(() => expect(cariesCheckbox.checked).toBe(true))
    expect(screen.getByText(/Editando el registro capturado el/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }))

    await waitFor(() =>
      expect(endoApi.annulInterrogation).toHaveBeenCalledWith('pat-1', 'interr-1', 'Corrección de datos'),
    )
    expect(endoApi.createInterrogation).toHaveBeenCalledWith(
      'pat-1',
      expect.objectContaining({ antecedentes: { caries: true } }),
    )
  })

  it('odontograma de diagnostico de endodoncia: selecciona un codigo para una pieza y guarda', async () => {
    vi.mocked(endoApi.createToothDiagnosisCode).mockResolvedValue({
      id: 'tdc-1',
      encounter_id: 'enc-hoy',
      tooth_fdi: '11',
      kind: 'diagnostico',
      code: 1,
      is_active: true,
      origin: 'MANUAL',
      created_at: new Date().toISOString(),
    })

    renderTab()
    // Espera a que la atencion de hoy se preseleccione antes de interactuar
    // con la grilla -- si no, el <select> de la pieza podria seguir
    // deshabilitado (sin encounterId) en el primer tick.
    await waitFor(() =>
      expect((screen.getByLabelText('Atencion') as HTMLSelectElement).value).toBe('enc-hoy'),
    )
    await userEvent.selectOptions(screen.getByLabelText('Odontograma de diagnostico pieza 11'), '1')

    await waitFor(() =>
      expect(endoApi.createToothDiagnosisCode).toHaveBeenCalledWith('pat-1', {
        encounter_id: 'enc-hoy',
        tooth_fdi: '11',
        kind: 'diagnostico',
        code: 1,
      }),
    )
  })

  it('boton de PDF abre una pestana nueva y navega a la URL del blob', async () => {
    vi.mocked(endoApi.getEndodonticHistoryPdfBlobUrl).mockResolvedValue('blob:mock-pdf')
    const openSpy = vi.spyOn(window, 'open').mockReturnValue({ location: { href: '' } } as never)

    renderTab()
    await userEvent.click(screen.getByRole('button', { name: 'Imprimir / Generar PDF' }))

    await waitFor(() => expect(endoApi.getEndodonticHistoryPdfBlobUrl).toHaveBeenCalledWith('pat-1'))
    expect(openSpy).toHaveBeenCalled()
    openSpy.mockRestore()
  })

  it('sin permiso de escritura, no se muestran los formularios de captura', async () => {
    renderTab(false)
    await screen.findByText('Interrogatorio')
    expect(screen.queryByRole('button', { name: 'Guardar interrogatorio' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Atencion')).not.toBeInTheDocument()
  })
})
