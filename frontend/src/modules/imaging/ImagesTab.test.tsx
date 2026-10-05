import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ImagesTab } from './ImagesTab'
import * as api from './api'
import type { ImageOut } from './types'

vi.mock('./api')
vi.mock('../encounters/api')
import * as encountersApi from '../encounters/api'

const image: ImageOut = {
  id: 'img-1',
  encounter_id: 'enc-1',
  study_type: 'periapical',
  tooth_fdi: 36,
  procedure_planned_id: null,
  procedure_performed_id: null,
  content_type: 'image/jpeg',
  original_filename: 'rx36.jpg',
  notes: null,
  has_thumbnail: true,
  is_active: true,
  created_at: '2026-10-05T12:00:00Z',
}

function renderTab(canWrite = true) {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <ImagesTab patientId="pat-1" canWrite={canWrite} />
    </QueryClientProvider>,
  )
}

describe('ImagesTab', () => {
  beforeEach(() => {
    vi.mocked(api.listImages).mockReset().mockResolvedValue([image])
    vi.mocked(api.getThumbnailBlobUrl).mockReset().mockResolvedValue('blob:thumb')
    vi.mocked(api.getImageBlobUrl).mockReset().mockResolvedValue('blob:full')
    vi.mocked(api.uploadImages).mockReset()
    vi.mocked(api.annulImage).mockReset()
    vi.mocked(encountersApi.listPatientEncounters).mockReset().mockResolvedValue([
      {
        id: 'enc-1',
        patient_id: 'pat-1',
        professional_id: 'prof-1',
        appointment_id: null,
        started_at: '2026-10-05T12:00:00Z',
        ended_at: null,
        chief_complaint: 'Control',
      },
    ])
  })

  it('muestra la galeria con la pieza de cada imagen', async () => {
    renderTab()
    expect(await screen.findByText(/Pieza 36/)).toBeInTheDocument()
  })

  it('el boton de subir esta deshabilitado sin archivos seleccionados', async () => {
    renderTab()
    await screen.findByText(/Pieza 36/)
    const button = screen.getByRole('button', { name: /Subir archivo/ })
    expect(button).toBeDisabled()
  })

  it('oculta el formulario de carga sin permiso de escritura', async () => {
    renderTab(false)
    await screen.findByText(/Pieza 36/)
    expect(screen.queryByRole('button', { name: /Subir/ })).not.toBeInTheDocument()
  })
})
