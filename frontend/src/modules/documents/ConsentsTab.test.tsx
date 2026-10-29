import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ConsentsTab } from './ConsentsTab'
import * as api from './api'
import { TEMPLATE_CODE_LABELS } from './catalog'
import type { ConsentOut, DocumentTemplateOut, TemplateCode } from './types'

vi.mock('./api')
vi.mock('../encounters/api')
vi.mock('../treatment/api')
vi.mock('../document_settings/api')
import * as encountersApi from '../encounters/api'
import * as treatmentApi from '../treatment/api'
import * as documentSettingsApi from '../document_settings/api'

function makeTemplate(code: TemplateCode): DocumentTemplateOut {
  return {
    id: `tpl-${code}`,
    code,
    name: TEMPLATE_CODE_LABELS[code],
    version: 1,
    html_content: '<p>Autorizo a {{paciente.nombre}}.</p>',
    is_current: true,
    created_at: '2026-10-05T12:00:00Z',
  }
}

const tomaRadiografias = makeTemplate('toma_radiografias')
const avisoPrivacidad = makeTemplate('aviso_privacidad')

const consent: ConsentOut = {
  id: 'consent-1',
  patient_id: 'pat-1',
  encounter_id: 'enc-1',
  template_id: 'tpl-toma_radiografias',
  procedure_planned_id: null,
  treatment_plan_id: null,
  professional_id: 'prof-1',
  signer_name: 'Jose Perez',
  signer_relationship: 'paciente',
  extra_fields: null,
  witness1_name: null,
  witness2_name: null,
  content_hash: 'abc123',
  signed_at: '2026-10-05T12:00:00Z',
  is_active: true,
  annul_reason: null,
}

function renderTab(canWrite = true, canSign = true) {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <ConsentsTab
        patientId="pat-1"
        patientName="Jose Perez"
        patientAge={30}
        canWrite={canWrite}
        canSign={canSign}
      />
    </QueryClientProvider>,
  )
}

async function selectEncounterAndTemplate(buttonName: string) {
  const encounterSelect = (await screen.findAllByLabelText('Atencion'))[0]
  await waitFor(() => expect(encounterSelect).toHaveTextContent('Dolor'))
  await userEvent.selectOptions(encounterSelect, 'enc-1')
  await userEvent.click(screen.getByRole('button', { name: buttonName }))
}

describe('ConsentsTab', () => {
  beforeEach(() => {
    vi.mocked(api.listTemplates).mockReset().mockResolvedValue([tomaRadiografias, avisoPrivacidad])
    vi.mocked(api.listConsents).mockReset().mockResolvedValue([consent])
    vi.mocked(api.createConsent).mockReset()
    vi.mocked(api.annulConsent).mockReset()
    vi.mocked(api.getConsentPrefill)
      .mockReset()
      .mockResolvedValue({
        variables: { paciente: { nombre: 'Jose Perez', edad: 30, expediente: 'EXP-1' } },
        extra_fields: {},
      })
    vi.mocked(documentSettingsApi.getDocumentSettings).mockReset().mockResolvedValue({
      institutional_title: null,
      place_label: null,
      logo_left_url: null,
      logo_right_url: null,
      has_logo_left: false,
      has_logo_right: false,
    })
    vi.mocked(encountersApi.listPatientEncounters)
      .mockReset()
      .mockResolvedValue([
        {
          id: 'enc-1',
          patient_id: 'pat-1',
          professional_id: 'prof-1',
          appointment_id: null,
          started_at: '2026-10-05T12:00:00Z',
          ended_at: null,
          chief_complaint: 'Dolor',
        },
      ])
    vi.mocked(treatmentApi.listPlans).mockReset().mockResolvedValue([])
  })

  it('el menu "Plantillas" agrupa por categoria, cerrada por defecto', async () => {
    renderTab()
    const summary = await screen.findByText('Consentimientos informados (1)')
    const details = summary.closest('details') as HTMLDetailsElement
    expect(details.open).toBe(false)
  })

  it('una categoria con 5 formatos o menos los lista; con mas de 5 usa un select alfabetico', async () => {
    const manyCodes: TemplateCode[] = [
      'toma_radiografias',
      'aplicacion_fluor',
      'limpieza_dental',
      'endodoncia',
      'exodoncia',
      'protesis_fija',
    ]
    vi.mocked(api.listTemplates).mockResolvedValue([
      ...manyCodes.map(makeTemplate),
      avisoPrivacidad,
    ])
    renderTab()

    // Aviso de privacidad: 1 sola opcion -> lista de botones, no select.
    expect(await screen.findByRole('button', { name: 'Aviso de privacidad' })).toBeInTheDocument()

    // Consentimientos informados: 6 opciones -> select alfabetico, sin botones individuales.
    const select = screen
      .getByText('Selecciona un formato...')
      .closest('select') as HTMLSelectElement
    const optionLabels = Array.from(select.querySelectorAll('option'))
      .slice(1)
      .map((o) => o.textContent)
    expect(optionLabels).toEqual(
      [...optionLabels].sort((a, b) => (a ?? '').localeCompare(b ?? '', 'es')),
    )
    expect(optionLabels).toHaveLength(6)
    expect(
      screen.queryByRole('button', { name: 'Procedimiento endodóntico' }),
    ).not.toBeInTheDocument()
  })

  it('elegir un formato pide el prefill y muestra el documento con los datos conocidos', async () => {
    renderTab()
    await selectEncounterAndTemplate('Toma de radiografías')

    expect(await screen.findByText('TOMA DE RADIOGRAFÍAS')).toBeInTheDocument()
    expect(screen.getAllByText(/Jose Perez/).length).toBeGreaterThan(0)
    await waitFor(() =>
      expect(api.getConsentPrefill).toHaveBeenCalledWith('pat-1', 'toma_radiografias', 'enc-1'),
    )
  })

  it('senala los campos obligatorios faltantes y permite editarlos antes de volver al documento', async () => {
    vi.mocked(api.getConsentPrefill).mockResolvedValue({
      variables: { paciente: { nombre: 'Jose Perez', edad: 30, expediente: 'EXP-1' } },
      extra_fields: {
        tipo_protesis: {
          label: 'Tipo de prótesis a colocar',
          required: true,
          multiline: false,
          value: null,
        },
      },
    })
    renderTab()
    await selectEncounterAndTemplate('Toma de radiografías')

    expect(await screen.findByText(/Faltan datos obligatorios/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Completar' }))

    await userEvent.type(screen.getByLabelText(/Tipo de prótesis a colocar/), 'Corona')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar y ver documento' }))

    expect(screen.queryByText(/Faltan datos obligatorios/)).not.toBeInTheDocument()
  })

  it('"Imprimir / Generar PDF" permanece deshabilitado hasta llenar nombre y firma', async () => {
    renderTab()
    await selectEncounterAndTemplate('Toma de radiografías')

    const plantillas = screen.getByText('Plantillas').closest('details') as HTMLDetailsElement
    const submitButton = await within(plantillas).findByRole('button', {
      name: 'Imprimir / Generar PDF',
    })
    expect(submitButton).toBeDisabled()

    await userEvent.type(screen.getByPlaceholderText('Nombre de quien firma'), 'Jose Perez')
    expect(submitButton).toBeDisabled() // todavia falta la firma en el canvas
  })

  it('oculta el formulario de firma sin permiso, pero deja ver el documento', async () => {
    renderTab(true, false)
    await selectEncounterAndTemplate('Toma de radiografías')

    expect(await screen.findByText('TOMA DE RADIOGRAFÍAS')).toBeInTheDocument()
    const plantillas = screen.getByText('Plantillas').closest('details') as HTMLDetailsElement
    expect(within(plantillas).queryByText('Imprimir / Generar PDF')).not.toBeInTheDocument()
  })

  it('anular un consentimiento pide motivo y llama a la API', async () => {
    vi.mocked(api.annulConsent).mockResolvedValue({ ...consent, is_active: false })
    renderTab()
    await selectEncounterAndTemplate('Toma de radiografías')

    await userEvent.click(await screen.findByRole('button', { name: 'Anular' }))
    await userEvent.type(screen.getByPlaceholderText('Motivo de anulacion'), 'Error de paciente')
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar' }))

    await waitFor(() =>
      expect(api.annulConsent).toHaveBeenCalledWith('consent-1', 'Error de paciente'),
    )
  })
})
