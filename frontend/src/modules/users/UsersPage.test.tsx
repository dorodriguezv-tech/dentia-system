import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as agendaApi from '../agenda/api'
import type { ResourceOut } from '../agenda/types'
import { useAuthStore } from '../auth/store'
import * as api from './api'
import { UsersPage } from './UsersPage'

vi.mock('./api')
vi.mock('../agenda/api')

function renderPage() {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <UsersPage />
    </QueryClientProvider>,
  )
}

const activeResource: ResourceOut = { id: 'res-active', name: 'Gabinete Centro', is_active: true }
const otherResource: ResourceOut = { id: 'res-norte', name: 'Gabinete Norte', is_active: true }

describe('UsersPage', () => {
  beforeEach(() => {
    useAuthStore.setState({
      clinics: [
        {
          clinic: { id: 'clinic-1', name: 'Sucursal Centro' },
          role: { code: 'admin_clinica', name: 'Administrador' },
        },
        {
          clinic: { id: 'clinic-2', name: 'Sucursal Norte' },
          role: { code: 'admin_clinica', name: 'Administrador' },
        },
      ],
      activeClinicId: 'clinic-1',
    })
    vi.mocked(api.listUsers).mockReset().mockResolvedValue([])
    vi.mocked(api.createUser).mockReset().mockResolvedValue({
      user: {
        id: 'u1',
        email: 'nuevo@example.com',
        full_name: 'Nuevo Usuario',
        is_active: true,
        mfa_enabled: false,
        mfa_setup_required: false,
      },
      role: { code: 'odontologo', name: 'Odontologo' },
    })
    vi.mocked(agendaApi.listResources).mockReset().mockImplementation((clinicId) =>
      Promise.resolve(clinicId === 'clinic-2' ? [otherResource] : [activeResource]),
    )
  })

  it('el gabinete por defecto solo se muestra para roles que atienden pacientes', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: 'Agregar usuario' }))

    // Por defecto el primer rol de ROLES es admin_clinica -- sin gabinete.
    expect(screen.queryByLabelText('Gabinete por defecto')).not.toBeInTheDocument()

    await userEvent.selectOptions(screen.getByLabelText('Rol'), 'odontologo')
    expect(await screen.findByLabelText('Gabinete por defecto')).toBeInTheDocument()
  })

  it('muestra las demas sucursales donde el administrador tambien administra usuarios', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: 'Agregar usuario' }))

    expect(screen.getByText('Sucursal Norte')).toBeInTheDocument()
    expect(screen.queryByText('Sucursal Centro')).not.toBeInTheDocument()
  })

  it('crea un usuario con gabinete por defecto y una sucursal adicional', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: 'Agregar usuario' }))

    await userEvent.type(screen.getByLabelText('Correo'), 'nuevo@example.com')
    await userEvent.type(screen.getByLabelText('Nombre completo'), 'Nuevo Usuario')
    await userEvent.type(screen.getByLabelText('Contrasena temporal'), 'Contrasena123')
    await userEvent.selectOptions(screen.getByLabelText('Rol'), 'odontologo')

    await userEvent.selectOptions(
      await screen.findByLabelText('Gabinete por defecto'),
      'res-active',
    )

    await userEvent.click(screen.getByText('Sucursal Norte'))
    await userEvent.selectOptions(
      await screen.findByLabelText('Gabinete por defecto en Sucursal Norte'),
      'res-norte',
    )

    await userEvent.click(screen.getByRole('button', { name: 'Crear' }))

    expect(vi.mocked(api.createUser).mock.calls[0]?.[0]).toEqual({
      email: 'nuevo@example.com',
      full_name: 'Nuevo Usuario',
      password: 'Contrasena123',
      role_code: 'odontologo',
      default_resource_id: 'res-active',
      additional_clinics: [{ clinic_id: 'clinic-2', default_resource_id: 'res-norte' }],
    })
  })
})
