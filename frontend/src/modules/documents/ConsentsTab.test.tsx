import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ConsentsTab } from './ConsentsTab'
import * as api from './api'
import type { ConsentOut, DocumentTemplateOut } from './types'

vi.mock('./api')
vi.mock('../encounters/api')
vi.mock('../treatment/api')
import * as encountersApi from '../encounters/api'
import * as treatmentApi from '../treatment/api'

const template: DocumentTemplateOut = {
  id: 'tpl-1',
  code: 'toma_radiografias',
  name: 'Toma de radiografías',
  version: 1,
  html_content: '<p>Autorizo</p>',
  is_current: true,
  created_at: '2026-10-05T12:00:00Z',
}

const consent: ConsentOut = {
  id: 'consent-1',
  patient_id: 'pat-1',
  encounter_id: 'enc-1',
  template_id: 'tpl-1',
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

describe('ConsentsTab', () => {
  beforeEach(() => {
    vi.mocked(api.listTemplates).mockReset().mockResolvedValue([template])
    vi.mocked(api.listConsents).mockReset().mockResolvedValue([consent])
    vi.mocked(api.createConsent).mockReset()
    vi.mocked(api.annulConsent).mockReset()
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

  it('muestra las plantillas y los consentimientos firmados', async () => {
    renderTab()
    expect(await screen.findByRole('button', { name: /Toma de radiografías/ })).toBeInTheDocument()
    expect(await screen.findByText(/Jose Perez/)).toBeInTheDocument()
  })

  it('anular un consentimiento pide motivo y llama a la API', async () => {
    vi.mocked(api.annulConsent).mockResolvedValue({ ...consent, is_active: false })
    renderTab()

    await screen.findByText(/Jose Perez/)
    await userEvent.click(screen.getByRole('button', { name: 'Anular' }))
    await userEvent.type(screen.getByPlaceholderText('Motivo de anulacion'), 'Error de paciente')
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar' }))

    await waitFor(() =>
      expect(api.annulConsent).toHaveBeenCalledWith('consent-1', 'Error de paciente'),
    )
  })

  it('oculta el formulario de firma cuando no se tiene permiso', async () => {
    renderTab(true, false)
    await screen.findByText(/Jose Perez/)
    expect(screen.queryByText('Firmar y generar PDF')).not.toBeInTheDocument()
  })

  it('no permite crear plantillas nuevas, pero si ver como se verian al hacer clic', async () => {
    renderTab()
    await screen.findByText(/Jose Perez/)
    expect(screen.queryByText('Guardar nueva version')).not.toBeInTheDocument()
    expect(screen.queryByPlaceholderText('Nombre de la plantilla')).not.toBeInTheDocument()

    expect(screen.queryByText('Autorizo')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /Toma de radiografías/ }))
    expect(await screen.findByText('Autorizo')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /Toma de radiografías/ }))
    expect(screen.queryByText('Autorizo')).not.toBeInTheDocument()
  })

  it('el selector de formatos agrupa por categoria', async () => {
    renderTab()
    await screen.findByText(/Jose Perez/)
    const select = screen
      .getByText('Selecciona un formato...')
      .closest('select') as HTMLSelectElement
    const groupLabels = Array.from(select.querySelectorAll('optgroup')).map((g) => g.label)
    expect(groupLabels).toEqual(['Consentimientos informados'])
  })

  it('el paso 2 no aparece hasta elegir un formato, y pide el prefill al elegirlo', async () => {
    vi.mocked(api.getConsentPrefill).mockResolvedValue({
      variables: { paciente: { nombre: 'Jose Perez', edad: 30, expediente: 'EXP-1' } },
      extra_fields: {},
    })
    renderTab()
    await screen.findByText(/Jose Perez/)

    expect(screen.queryByText('Datos correctos, continuar')).not.toBeInTheDocument()

    await userEvent.selectOptions(screen.getAllByLabelText('Atencion')[0], 'enc-1')
    const select = screen
      .getByText('Selecciona un formato...')
      .closest('select') as HTMLSelectElement
    await userEvent.selectOptions(select, 'toma_radiografias')

    expect(await screen.findByText('Datos correctos, continuar')).toBeInTheDocument()
    await waitFor(() =>
      expect(api.getConsentPrefill).toHaveBeenCalledWith('pat-1', 'toma_radiografias', 'enc-1'),
    )
    // Sin campos extra para este formato: no hay ninguna seccion de "Falta completar".
    expect(screen.queryByText('Falta completar')).not.toBeInTheDocument()
  })

  it('el boton de firmar permanece deshabilitado hasta confirmar los datos y llenar lo obligatorio', async () => {
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
    await screen.findByText(/Jose Perez/)

    await userEvent.selectOptions(screen.getAllByLabelText('Atencion')[0], 'enc-1')
    const select = screen
      .getByText('Selecciona un formato...')
      .closest('select') as HTMLSelectElement
    await userEvent.selectOptions(select, 'toma_radiografias')
    await userEvent.click(await screen.findByText('Datos correctos, continuar'))

    const submitButton = screen.getByRole('button', { name: 'Firmar y generar PDF' })
    expect(submitButton).toBeDisabled()

    await userEvent.type(screen.getByLabelText(/Tipo de prótesis a colocar/), 'Corona')
    await userEvent.type(screen.getByPlaceholderText('Nombre de quien firma'), 'Jose Perez')
    expect(submitButton).toBeDisabled() // todavia falta la firma en el canvas
  })
})
