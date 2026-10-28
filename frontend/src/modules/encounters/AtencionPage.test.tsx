import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AtencionPage } from './AtencionPage'
import type { ClinicalNoteOut, EncounterOut } from './types'

vi.mock('./api')
vi.mock('../records/api')
import * as recordsApi from '../records/api'
import * as api from './api'

const encounter: EncounterOut = {
  id: 'enc-1',
  patient_id: 'pat-1',
  professional_id: 'prof-1',
  appointment_id: null,
  chief_complaint: 'Dolor al frio',
  started_at: '2026-01-10T12:00:00Z',
  ended_at: null,
}

const draftNote: ClinicalNoteOut = {
  id: 'note-1',
  encounter_id: 'enc-1',
  patient_id: 'pat-1',
  author_id: 'prof-1',
  status: 'DRAFT',
  soap_s: 'Dolor leve',
  soap_o: null,
  soap_a: null,
  soap_p: null,
  free_text: null,
  interrogatorio: null,
  medicamentos: null,
  estudios_radiograficos: null,
  descripcion_procedimiento: null,
  pronostico_evolucion: null,
  indicaciones: null,
  plan_proxima_cita: null,
  fecha_proxima_cita: null,
  evaluacion_actualizacion: null,
  version: 1,
  previous_version_id: null,
  correction_reason: null,
  content_hash: null,
  finalized_at: null,
  cancel_reason: null,
  updated_at: '2026-01-10T12:00:00Z',
}

function renderPage() {
  const queryClient = new QueryClient()
  const router = createMemoryRouter(
    [
      { path: '/pacientes/:patientId/atencion/:encounterId', element: <AtencionPage /> },
      { path: '/pacientes/:id', element: <div>Ficha del paciente</div> },
    ],
    { initialEntries: ['/pacientes/pat-1/atencion/enc-1'] },
  )
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

describe('AtencionPage', () => {
  beforeEach(() => {
    vi.mocked(api.getEncounter).mockReset().mockResolvedValue(encounter)
    vi.mocked(api.listEncounterNotes).mockReset().mockResolvedValue([draftNote])
    vi.mocked(api.createNote).mockReset()
    vi.mocked(api.updateNote).mockReset()
    vi.mocked(api.finalizeNote).mockReset()
    vi.mocked(api.correctNote).mockReset()
    vi.mocked(api.cancelNote).mockReset()
    vi.mocked(recordsApi.getPatientAlerts).mockReset()
  })

  it('exige confirmar las alertas criticas antes de finalizar cuando el paciente tiene alertas activas', async () => {
    vi.mocked(recordsApi.getPatientAlerts).mockResolvedValue(['Alergia severa: Penicilina'])
    vi.mocked(api.finalizeNote).mockResolvedValue({ ...draftNote, status: 'FINAL' })

    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: 'Finalizar nota' }))

    expect(await screen.findByText('Alertas criticas del paciente')).toBeInTheDocument()
    expect(screen.getByText('Alergia severa: Penicilina')).toBeInTheDocument()
    expect(api.finalizeNote).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: 'Confirmar y finalizar' }))

    await waitFor(() => expect(api.finalizeNote).toHaveBeenCalledWith('note-1', true))
  })

  it('finaliza directamente sin modal cuando el paciente no tiene alertas activas', async () => {
    vi.mocked(recordsApi.getPatientAlerts).mockResolvedValue([])
    vi.mocked(api.finalizeNote).mockResolvedValue({ ...draftNote, status: 'FINAL' })

    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: 'Finalizar nota' }))

    await waitFor(() => expect(api.finalizeNote).toHaveBeenCalledWith('note-1', false))
    expect(screen.queryByText('Alertas criticas del paciente')).not.toBeInTheDocument()
  })

  it('una nota FINAL no se puede editar y solo ofrece corregir o cancelar', async () => {
    vi.mocked(api.listEncounterNotes).mockResolvedValue([{ ...draftNote, status: 'FINAL' }])

    renderPage()

    const soapField = await screen.findByLabelText('Subjetivo')
    expect(soapField).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Finalizar nota' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Corregir' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancelar' })).toBeInTheDocument()
  })
})
