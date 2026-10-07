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

    expect(screen.getByText('DentalCare')).toBeInTheDocument()
    expect(screen.getByText('Buscar paciente...')).toBeInTheDocument()
  })

  it('A7: sin logo configurado, el nombre de la marca es un enlace a inicio', () => {
    renderLayout()

    const brandLink = screen.getByRole('link', { name: 'DentalCare' })
    expect(brandLink).toHaveAttribute('href', '/')
  })

  it('A7: con logo configurado, se muestra el logo (no el nombre) como enlace a inicio', () => {
    useThemeStore.setState({
      branding: {
        display_name: 'Clinica Dental Demo',
        subtitle: null,
        logo_url: '/branding/logo',
        favicon_url: null,
        contrast_warnings: [],
        preset: 'menta_clinica',
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

    expect(screen.queryByText('Clinica Dental Demo')).not.toBeInTheDocument()
    const brandLink = screen.getByRole('link', { name: '' })
    expect(brandLink).toHaveAttribute('href', '/')
    expect(brandLink.querySelector('img')).toBeInTheDocument()
  })
})
