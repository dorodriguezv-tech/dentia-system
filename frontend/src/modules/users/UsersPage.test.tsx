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

const existingUser = {
  user: {
    id: 'u-existente',
    email: 'existente@example.com',
    full_name: 'Usuario Existente',
    professional_license: null,
    is_active: true,
    mfa_enabled: false,
    mfa_setup_required: false,
    ai_enabled: true,
    has_photo: false,
  },
  role: { code: 'recepcion', name: 'Recepcion' },
}

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
        professional_license: '1234567',
        is_active: true,
        mfa_enabled: false,
        mfa_setup_required: false,
        ai_enabled: true,
        has_photo: false,
      },
      role: { code: 'odontologo', name: 'Odontologo' },
    })
    vi.mocked(agendaApi.listResources).mockReset().mockImplementation((clinicId) =>
      Promise.resolve(clinicId === 'clinic-2' ? [otherResource] : [activeResource]),
    )
    vi.mocked(api.updateUser).mockReset().mockResolvedValue(existingUser)
    vi.mocked(api.deleteUser).mockReset().mockResolvedValue(undefined)
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
    await userEvent.type(
      screen.getByLabelText('Contrasena temporal (minimo 12 caracteres)'),
      'Contrasena123',
    )
    await userEvent.selectOptions(screen.getByLabelText('Rol'), 'odontologo')

    await userEvent.type(await screen.findByLabelText('Cedula profesional'), '1234567')

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
      professional_license: '1234567',
      default_resource_id: 'res-active',
      additional_clinics: [{ clinic_id: 'clinic-2', default_resource_id: 'res-norte' }],
    })
  })

  // Bug real reportado: "al editar un usuario aparece 'Datos de entrada invalidos'".
  // Causa raiz: el input de "Contrasena temporal" aceptaba 8 caracteres (minLength
  // desalineado de app/core/password_policy.py::MIN_PASSWORD_LENGTH, que exige 12),
  // asi que el formulario dejaba enviar al backend una contrasena que este siempre
  // rechazaba con un 422 generico -- sin indicar que el problema era la contrasena.
  // No se prueba via el bloqueo nativo de envio del formulario (jsdom no implementa
  // minLength en su motor de validacion, a diferencia de un navegador real) sino
  // comprobando directamente el minLength configurado en el input, que es la causa
  // raiz exacta del bug.
  it('el input de contrasena temporal exige el minimo de la politica del backend (12 caracteres)', async () => {
    renderPage()
    await userEvent.click(screen.getByRole('button', { name: 'Agregar usuario' }))

    const passwordInput = screen.getByLabelText<HTMLInputElement>(
      'Contrasena temporal (minimo 12 caracteres)',
    )

    expect(passwordInput.minLength).toBe(12)
  })

  it('edita un usuario existente, incluida la contrasena', async () => {
    vi.mocked(api.listUsers).mockReset().mockResolvedValue([existingUser])
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: 'Editar' }))
    const nameInput = screen.getByDisplayValue('Usuario Existente')
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, 'Usuario Renombrado')
    await userEvent.type(
      screen.getByLabelText('Nueva contrasena (dejar en blanco para no cambiarla, minimo 12 caracteres)'),
      'NuevaContrasena123',
    )
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(vi.mocked(api.updateUser).mock.calls[0]).toEqual([
      'u-existente',
      {
        full_name: 'Usuario Renombrado',
        email: 'existente@example.com',
        role_code: 'recepcion',
        professional_license: null,
        new_password: 'NuevaContrasena123',
      },
    ])
  })

  // Mismo bug que el caso de arriba, pero en el formulario de editar (donde se
  // reporto originalmente): el input de "Nueva contrasena" tambien exige ahora el
  // minimo real de la politica (12).
  it('el input de nueva contrasena al editar exige el minimo de la politica del backend (12 caracteres)', async () => {
    vi.mocked(api.listUsers).mockReset().mockResolvedValue([existingUser])
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: 'Editar' }))
    const passwordInput = screen.getByLabelText<HTMLInputElement>(
      'Nueva contrasena (dejar en blanco para no cambiarla, minimo 12 caracteres)',
    )

    expect(passwordInput.minLength).toBe(12)
  })

  it(
    'el formulario de editar muestra el usuario (correo) con el que accesa, ' +
      'sin importar el rol, y permite cambiarlo',
    async () => {
      vi.mocked(api.listUsers).mockReset().mockResolvedValue([existingUser])
      renderPage()

      await userEvent.click(await screen.findByRole('button', { name: 'Editar' }))
      const emailInput = screen.getByDisplayValue('existente@example.com')
      await userEvent.clear(emailInput)
      await userEvent.type(emailInput, 'nuevo-correo@example.com')
      await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

      expect(vi.mocked(api.updateUser).mock.calls[0]?.[1]).toMatchObject({
        email: 'nuevo-correo@example.com',
      })
    },
  )

  it('borrar un usuario pide confirmar antes de llamar a la API', async () => {
    vi.mocked(api.listUsers).mockReset().mockResolvedValue([existingUser])
    renderPage()

    await userEvent.click(await screen.findByRole('button', { name: 'Borrar' }))
    expect(api.deleteUser).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: 'Confirmar' }))
    expect(api.deleteUser).toHaveBeenCalledWith('u-existente')
  })
})
