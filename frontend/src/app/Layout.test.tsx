import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { useThemeStore } from '../theme/store'
import { Layout } from './Layout'

function renderLayout() {
  const router = createMemoryRouter(
    [
      { path: '/', element: <Layout />, children: [{ index: true, element: <div>Inicio</div> }] },
      { path: '/pacientes', element: <Layout />, children: [{ index: true, element: <div /> }] },
    ],
    { initialEntries: ['/pacientes'] },
  )
  render(<RouterProvider router={router} />)
}

describe('Layout', () => {
  beforeEach(() => {
    useThemeStore.setState({ branding: null })
  })

  it('muestra la marca y el titulo del encabezado', () => {
    renderLayout()

    expect(screen.getByText('Buscar paciente...')).toBeInTheDocument()
  })

  it('A7/W7: sin logo propio, el enlace a inicio muestra el logo DENT-IA', () => {
    renderLayout()

    const brandLink = screen.getByRole('link', {
      name: 'DENT-IA · Sistema Inteligente de Gestión Odontológica',
    })
    expect(brandLink).toHaveAttribute('href', '/')
    expect(brandLink.querySelector('img')).toBeInTheDocument()
  })

  it('A7/W7: con logo propio, se muestra el logo de la clinica (no el de DENT-IA)', () => {
    useThemeStore.setState({
      branding: {
        display_name: 'Clinica Dental Demo',
        subtitle: null,
        logo_url: '/branding/logo',
        favicon_url: null,
        has_custom_logo: true,
        contrast_warnings: [],
        preset: 'dentia',
        colors: {
          primary: '#000',
          secondary: '#000',
          accent: '#000',
          bg: '#fff',
          surface: '#fff',
          border: '#000',
          text: '#000',
          text_muted: '#000',
          success: '#000',
          warning: '#000',
          danger: '#000',
        },
        dark_mode: false,
        radius: 'soft',
      },
    })

    renderLayout()

    const brandLink = screen.getByRole('link', { name: 'Logo de Clinica Dental Demo' })
    expect(brandLink).toHaveAttribute('href', '/')
    expect(brandLink.querySelector('img')).toBeInTheDocument()
  })
})
