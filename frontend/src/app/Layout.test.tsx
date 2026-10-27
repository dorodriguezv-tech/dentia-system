import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as agendaApi from '../modules/agenda/api'
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

// EnSalaAlert (banner de "paciente en sala") pide /providers y /appointments --
// sin mock, un rol odontologo/especialista en estos tests dispararia llamadas
// reales via apiRequest (fetch) que jsdom no puede resolver.
vi.mock('../modules/agenda/api')

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
    has_photo: false,
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
  const queryClient = new QueryClient()
  const router = createMemoryRouter(
    [
      { path: '/', element: <Layout />, children: [{ index: true, element: <div>Inicio</div> }] },
      { path: '/pacientes', element: <Layout />, children: [{ index: true, element: <div /> }] },
      {
        path: '/pacientes/:patientId/atencion/:encounterId',
        element: <div>Pantalla de atencion</div>,
      },
    ],
    { initialEntries: ['/pacientes'] },
  )
  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
}

function odontologoProvider(userId: string) {
  return {
    id: 'prov-1',
    user_id: userId,
    full_name: 'Odontologo de prueba',
    color: '#000000',
    is_active: true,
    default_resource_id: null,
  }
}

describe('Layout', () => {
  beforeEach(() => {
    useThemeStore.setState({ branding: null })
    useAuthStore.setState({ user: null, clinics: [], activeClinicId: null })
    vi.mocked(agendaApi.listProviders).mockReset().mockResolvedValue([])
    vi.mocked(agendaApi.listAppointments).mockReset().mockResolvedValue([])
    vi.mocked(agendaApi.startEncounter).mockReset()
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

  describe('EnSalaAlert (paciente en sala)', () => {
    function enSalaAppointment() {
      return {
        id: 'appt-1',
        patient_id: 'pat-1',
        patient_full_name: 'Paciente de Prueba',
        provider_id: 'prov-1',
        provider_full_name: 'Odontologo de prueba',
        provider_color: '#000000',
        resource_id: null,
        resource_name: null,
        appointment_type: 'consulta',
        starts_at: new Date().toISOString(),
        ends_at: new Date().toISOString(),
        status: 'EN_SALA' as const,
        notes: null,
      }
    }

    it('muestra el banner cuando el profesional logueado tiene una cita propia en EN_SALA', async () => {
      useAuthStore.setState({
        user: odontologoUser(false),
        clinics: odontologoClinics(),
        activeClinicId: 'c1',
      })
      vi.mocked(agendaApi.listProviders).mockResolvedValue([odontologoProvider('u1')])
      vi.mocked(agendaApi.listAppointments).mockResolvedValue([enSalaAppointment()])

      renderLayout()

      expect(await screen.findByText('Paciente en sala de espera')).toBeInTheDocument()
      expect(screen.getByText(/Paciente de Prueba/)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Iniciar atencion' })).toBeInTheDocument()
    })

    it('no muestra el banner para un rol que no puede escribir expedientes (recepcion)', async () => {
      useAuthStore.setState({
        user: odontologoUser(false),
        clinics: [{ clinic: { id: 'c1', name: 'Sucursal Centro' }, role: { code: 'recepcion', name: 'Recepcion' } }],
        activeClinicId: 'c1',
      })
      vi.mocked(agendaApi.listProviders).mockResolvedValue([odontologoProvider('u1')])
      vi.mocked(agendaApi.listAppointments).mockResolvedValue([enSalaAppointment()])

      renderLayout()

      await waitFor(() => {
        expect(agendaApi.listAppointments).not.toHaveBeenCalled()
      })
      expect(screen.queryByText('Paciente en sala de espera')).not.toBeInTheDocument()
    })

    it('no muestra el banner si no hay ninguna cita en EN_SALA', async () => {
      useAuthStore.setState({
        user: odontologoUser(false),
        clinics: odontologoClinics(),
        activeClinicId: 'c1',
      })
      vi.mocked(agendaApi.listProviders).mockResolvedValue([odontologoProvider('u1')])
      vi.mocked(agendaApi.listAppointments).mockResolvedValue([])

      renderLayout()

      await waitFor(() => {
        expect(agendaApi.listAppointments).toHaveBeenCalled()
      })
      expect(screen.queryByText('Paciente en sala de espera')).not.toBeInTheDocument()
    })

    it('al hacer clic en "Iniciar atencion" llama a start-encounter y navega a la pantalla de atencion', async () => {
      useAuthStore.setState({
        user: odontologoUser(false),
        clinics: odontologoClinics(),
        activeClinicId: 'c1',
      })
      vi.mocked(agendaApi.listProviders).mockResolvedValue([odontologoProvider('u1')])
      vi.mocked(agendaApi.listAppointments).mockResolvedValue([enSalaAppointment()])
      vi.mocked(agendaApi.startEncounter).mockResolvedValue({
        id: 'enc-1',
        patient_id: 'pat-1',
        professional_id: 'prov-1',
        appointment_id: 'appt-1',
        chief_complaint: null,
        started_at: new Date().toISOString(),
        ended_at: null,
      })

      renderLayout()

      const button = await screen.findByRole('button', { name: 'Iniciar atencion' })
      button.click()

      expect(await screen.findByText('Pantalla de atencion')).toBeInTheDocument()
      expect(vi.mocked(agendaApi.startEncounter).mock.calls[0][0]).toBe('appt-1')
    })
  })
})
