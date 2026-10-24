import { render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '../modules/auth/store'
import { useVoiceStore } from '../modules/voice/store'
import { useThemeStore } from '../theme/store'
import { Layout } from './Layout'

// El orbe (DentiaOrb) usa useVoiceSession para conectar un WebSocket real --
// sin este stub, su propio useEffect fuerza el estado a 'disconnected' en
// jsdom (sin servidor), pisando el estado que los tests de abajo necesitan
// fijar a mano (mismo patron que DentiaOrb.test.tsx).
vi.mock('../modules/voice/useVoiceSession', () => ({
  useVoiceSession: () => ({ toggleMute: vi.fn() }),
}))

function odontologoUser(aiEnabled: boolean) {
  return {
    id: 'u1',
    email: 'odonto@example.com',
    full_name: 'Odontologo de prueba',
    professional_license: null,
    is_active: true,
    mfa_enabled: false,
    mfa_setup_required: false,
    ai_enabled: aiEnabled,
  }
}

function odontologoClinics() {
  return [
    {
      clinic: { id: 'c1', name: 'Sucursal Centro' },
      role: { code: 'odontologo', name: 'Odontologo' },
    },
  ]
}

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
    useAuthStore.setState({ user: null, clinics: [], activeClinicId: null })
  })

  it('con AI_ENABLED=false, no muestra el orbe de Dentia aunque el rol pueda usar voz y este en escucha pasiva', () => {
    useVoiceStore.setState({ state: 'passive', subtitle: null, activeInAnotherTab: false })
    useAuthStore.setState({
      user: odontologoUser(false),
      clinics: odontologoClinics(),
      activeClinicId: 'c1',
    })

    renderLayout()

    expect(screen.queryByRole('button', { name: /Dentia/i })).not.toBeInTheDocument()
  })

  it('con AI_ENABLED=true, si muestra el orbe de Dentia para un rol que puede usar voz', () => {
    useVoiceStore.setState({ state: 'passive', subtitle: null, activeInAnotherTab: false })
    useAuthStore.setState({
      user: odontologoUser(true),
      clinics: odontologoClinics(),
      activeClinicId: 'c1',
    })

    renderLayout()

    expect(screen.getByRole('button', { name: /Dentia/i })).toBeInTheDocument()
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
