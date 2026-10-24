import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { LoginPage } from './LoginPage'
import { useAuthStore } from './store'
import type { MyClinicOut, TokenResponse } from './types'

vi.mock('./api')
import * as api from './api'

const clinic: MyClinicOut = {
  clinic: { id: 'c1', name: 'Sucursal Centro' },
  role: { code: 'odontologo', name: 'Odontologo' },
}

const tokens: TokenResponse = {
  access_token: 'access',
  refresh_token: 'refresh',
  token_type: 'bearer',
  expires_in: 900,
  user: {
    id: 'u1',
    email: 'odonto@example.com',
    full_name: 'Dra. Prueba',
    professional_license: null,
    is_active: true,
    mfa_enabled: false,
    mfa_setup_required: false,
    ai_enabled: true,
  },
}

const initialState = useAuthStore.getState()

function renderLoginPage() {
  const router = createMemoryRouter(
    [
      { path: '/login', element: <LoginPage /> },
      { path: '/', element: <div>Pagina de inicio</div> },
      { path: '/seleccionar-sucursal', element: <div>Selecciona tu sucursal</div> },
    ],
    { initialEntries: ['/login'] },
  )
  render(<RouterProvider router={router} />)
}

describe('LoginPage', () => {
  beforeEach(() => {
    useAuthStore.setState(initialState, true)
    vi.mocked(api.getMyClinics).mockResolvedValue([clinic])
  })

  it('inicia sesion y navega al inicio cuando no hay MFA', async () => {
    vi.mocked(api.login).mockResolvedValue(tokens)
    renderLoginPage()

    await userEvent.type(screen.getByLabelText('Correo'), 'odonto@example.com')
    await userEvent.type(screen.getByLabelText('Contrasena'), 'Contrasena123')
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    await waitFor(() => expect(screen.getByText('Pagina de inicio')).toBeInTheDocument())
    expect(useAuthStore.getState().user?.email).toBe('odonto@example.com')
  })

  it('pide el codigo MFA y despues inicia sesion', async () => {
    vi.mocked(api.login).mockResolvedValue({ mfa_required: true, mfa_token: 'mfa-token' })
    vi.mocked(api.loginMfa).mockResolvedValue(tokens)
    renderLoginPage()

    await userEvent.type(screen.getByLabelText('Correo'), 'admin@example.com')
    await userEvent.type(screen.getByLabelText('Contrasena'), 'Contrasena123')
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    const codeInput = await screen.findByLabelText('Codigo de verificacion')
    await userEvent.type(codeInput, '123456')
    await userEvent.click(screen.getByRole('button', { name: 'Verificar' }))

    await waitFor(() => expect(screen.getByText('Pagina de inicio')).toBeInTheDocument())
    expect(api.loginMfa).toHaveBeenCalledWith('mfa-token', '123456')
  })

  it('muestra un error cuando las credenciales son invalidas', async () => {
    const { ApiRequestError } = await import('../../api/client')
    vi.mocked(api.login).mockRejectedValue(
      new ApiRequestError(401, {
        code: 'INVALID_CREDENTIALS',
        message: 'Correo o contrasena incorrectos',
      }),
    )
    renderLoginPage()

    await userEvent.type(screen.getByLabelText('Correo'), 'odonto@example.com')
    await userEvent.type(screen.getByLabelText('Contrasena'), 'incorrecta')
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }))

    expect(await screen.findByText('Correo o contrasena incorrectos')).toBeInTheDocument()
  })
})
