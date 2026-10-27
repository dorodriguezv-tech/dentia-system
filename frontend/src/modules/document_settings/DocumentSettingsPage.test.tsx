import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DocumentSettingsPage } from './DocumentSettingsPage'

vi.mock('./api')
vi.mock('../../api/client', async () => {
  const actual =
    await vi.importActual<typeof import('../../api/client')>('../../api/client')
  return { ...actual, apiRequestBlobUrl: vi.fn() }
})
import { apiRequestBlobUrl } from '../../api/client'
import * as api from './api'

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <DocumentSettingsPage />
    </QueryClientProvider>,
  )
}

describe('DocumentSettingsPage', () => {
  beforeEach(() => {
    vi.mocked(api.getDocumentSettings).mockReset().mockResolvedValue({
      institutional_title: 'Clinica Odontologica Escuela',
      place_label: 'Ciudad de Mexico',
      logo_left_url: '/api/v1/document-settings/logo-left',
      logo_right_url: null,
      has_logo_left: true,
      has_logo_right: false,
    })
    vi.mocked(api.updateDocumentSettings).mockReset()
    vi.mocked(api.uploadLogo).mockReset()
    vi.mocked(apiRequestBlobUrl).mockReset().mockResolvedValue('blob:mock-logo')
  })

  it('carga y muestra el titulo institucional y el lugar guardados', async () => {
    renderPage()

    expect(
      await screen.findByDisplayValue('Clinica Odontologica Escuela'),
    ).toBeInTheDocument()
    expect(screen.getByDisplayValue('Ciudad de Mexico')).toBeInTheDocument()
    expect(await screen.findByAltText('Logo izquierdo')).toHaveAttribute('src', 'blob:mock-logo')
    expect(screen.getByText('Sin logo')).toBeInTheDocument()
  })

  it('guarda el titulo institucional y el lugar', async () => {
    vi.mocked(api.updateDocumentSettings).mockResolvedValue({
      institutional_title: 'Nuevo titulo',
      place_label: 'Ciudad de Mexico',
      logo_left_url: '/api/v1/document-settings/logo-left',
      logo_right_url: null,
      has_logo_left: true,
      has_logo_right: false,
    })

    renderPage()
    const titleInput = await screen.findByLabelText('Título institucional')
    await userEvent.clear(titleInput)
    await userEvent.type(titleInput, 'Nuevo titulo')
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    await waitFor(() =>
      expect(api.updateDocumentSettings).toHaveBeenCalledWith({
        institutional_title: 'Nuevo titulo',
        place_label: 'Ciudad de Mexico',
      }),
    )
    expect(await screen.findByText('Formatos de documentos guardados.')).toBeInTheDocument()
  })

  it('sube un logo nuevo', async () => {
    vi.mocked(api.uploadLogo).mockResolvedValue({
      institutional_title: 'Clinica Odontologica Escuela',
      place_label: 'Ciudad de Mexico',
      logo_left_url: '/api/v1/document-settings/logo-left',
      logo_right_url: '/api/v1/document-settings/logo-right',
      has_logo_left: true,
      has_logo_right: true,
    })

    renderPage()
    await screen.findByText('Sin logo')

    const file = new File(['logo'], 'logo.png', { type: 'image/png' })
    const fileInputs = document.querySelectorAll('input[type="file"]')
    await userEvent.upload(fileInputs[1] as HTMLInputElement, file)

    await waitFor(() => expect(api.uploadLogo).toHaveBeenCalledWith('right', file))
  })
})
