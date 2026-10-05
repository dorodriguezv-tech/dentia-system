import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError } from '../../api/client'
import * as recordsApi from '../records/api'
import { AiAssistant } from './AiAssistant'
import * as api from './api'
import type { AiSuggestionOut } from './types'

vi.mock('./api')
vi.mock('../records/api')

const pendingAllergy: AiSuggestionOut = {
  id: 'sugg-1',
  batch_id: 'batch-1',
  encounter_id: 'enc-1',
  action_type: 'add_allergy',
  payload: { substance: 'Penicilina' },
  status: 'PENDING',
  model_name: 'qwen2.5:7b',
  model_digest: null,
  transcript_excerpt: 'Alergica a la penicilina',
  created_at: '2026-10-05T12:00:00Z',
  reviewed_at: null,
  reject_reason: null,
}

function renderAssistant(onInsertFallbackText = vi.fn()) {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <AiAssistant patientId="pat-1" encounterId="enc-1" onInsertFallbackText={onInsertFallbackText} />
    </QueryClientProvider>,
  )
}

describe('AiAssistant', () => {
  beforeEach(() => {
    vi.mocked(api.listSuggestions).mockReset().mockResolvedValue([pendingAllergy])
    vi.mocked(recordsApi.getPatientAlerts).mockReset().mockResolvedValue([])
    vi.mocked(api.acceptSuggestion).mockReset()
    vi.mocked(api.rejectSuggestion).mockReset()
    vi.mocked(api.interpret).mockReset()
  })

  it('muestra las propuestas pendientes agrupadas por destino', async () => {
    renderAssistant()
    expect(await screen.findByText('Propuestas del asistente')).toBeInTheDocument()
    expect(screen.getByText('Expediente')).toBeInTheDocument()
    expect(screen.getByText('Penicilina')).toBeInTheDocument()
  })

  it('aceptar una propuesta llama a la API con su id', async () => {
    vi.mocked(api.acceptSuggestion).mockResolvedValue({ ...pendingAllergy, status: 'ACCEPTED' })
    renderAssistant()

    await screen.findByText('Propuestas del asistente')
    await userEvent.click(screen.getByRole('button', { name: 'Aceptar' }))

    await waitFor(() => expect(api.acceptSuggestion).toHaveBeenCalledWith('sugg-1', undefined))
  })

  it('rechazar una propuesta llama a la API con su id', async () => {
    vi.mocked(api.rejectSuggestion).mockResolvedValue({ ...pendingAllergy, status: 'REJECTED' })
    renderAssistant()

    await screen.findByText('Propuestas del asistente')
    await userEvent.click(screen.getByRole('button', { name: 'Rechazar' }))

    await waitFor(() => expect(api.rejectSuggestion).toHaveBeenCalledWith('sugg-1'))
  })

  it('interpretar un dictado vacio no habilita el boton', async () => {
    renderAssistant()
    const button = await screen.findByRole('button', { name: 'Interpretar dictado' })
    expect(button).toBeDisabled()
  })

  it('al escribir texto y pulsar interpretar, llama a la API con el transcript', async () => {
    vi.mocked(api.interpret).mockResolvedValue({ suggestions: [], unrecognized: [] })
    renderAssistant()

    const textarea = screen.getByPlaceholderText('Transcripcion del dictado (editable)...')
    await userEvent.type(textarea, 'Alergica a la penicilina')
    await userEvent.click(screen.getByRole('button', { name: 'Interpretar dictado' }))

    await waitFor(() =>
      expect(api.interpret).toHaveBeenCalledWith('enc-1', 'Alergica a la penicilina'),
    )
  })

  it('si Ollama no esta disponible (503), ofrece insertar como texto', async () => {
    vi.mocked(api.interpret).mockRejectedValue(
      new ApiRequestError(503, { code: 'AI_UNAVAILABLE', message: 'no disponible' }),
    )
    const onInsertFallbackText = vi.fn()
    renderAssistant(onInsertFallbackText)

    const textarea = screen.getByPlaceholderText('Transcripcion del dictado (editable)...')
    await userEvent.type(textarea, 'Dictado de prueba')
    await userEvent.click(screen.getByRole('button', { name: 'Interpretar dictado' }))

    const insertButton = await screen.findByRole('button', {
      name: 'Insertar como texto en la nota',
    })
    await userEvent.click(insertButton)
    expect(onInsertFallbackText).toHaveBeenCalledWith('Dictado de prueba')
  })
})
