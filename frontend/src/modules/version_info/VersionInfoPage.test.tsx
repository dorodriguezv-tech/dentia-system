import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { VersionInfoPage } from './VersionInfoPage'

vi.mock('./api')
import * as api from './api'

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <VersionInfoPage />
    </QueryClientProvider>,
  )
}

describe('VersionInfoPage', () => {
  beforeEach(() => {
    vi.mocked(api.getVersionInfo).mockReset()
  })

  it('muestra la version y el entorno desplegados', async () => {
    vi.mocked(api.getVersionInfo).mockResolvedValue({
      version: '1.2.3',
      environment: 'production',
    })

    renderPage()

    expect(await screen.findByText('1.2.3')).toBeInTheDocument()
    expect(screen.getByText('Producción')).toBeInTheDocument()
  })

  it('muestra un entorno desconocido tal cual, sin traducirlo', async () => {
    vi.mocked(api.getVersionInfo).mockResolvedValue({
      version: 'dev',
      environment: 'staging',
    })

    renderPage()

    expect(await screen.findByText('dev')).toBeInTheDocument()
    expect(screen.getByText('staging')).toBeInTheDocument()
  })

  it('ofrece un enlace al historial de versiones en GitHub', async () => {
    vi.mocked(api.getVersionInfo).mockResolvedValue({
      version: '1.2.3',
      environment: 'production',
    })

    renderPage()
    await screen.findByText('1.2.3')

    const link = screen.getByRole('link', { name: /historial de versiones en GitHub/i })
    expect(link).toHaveAttribute(
      'href',
      'https://github.com/dorodriguezv-tech/dentia-system/releases',
    )
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('muestra un mensaje de error si la consulta falla', async () => {
    vi.mocked(api.getVersionInfo).mockRejectedValue(new Error('network error'))

    renderPage()

    expect(
      await screen.findByText('No se pudo consultar la versión desplegada.'),
    ).toBeInTheDocument()
  })
})
