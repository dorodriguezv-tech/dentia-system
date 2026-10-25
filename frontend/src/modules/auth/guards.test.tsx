import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it } from 'vitest'
import { RequireRole } from './guards'
import { useAuthStore } from './store'

function renderGuarded(roles: string[]) {
  render(
    <MemoryRouter initialEntries={['/']}>
      <Routes>
        <Route element={<RequireRole roles={roles} />}>
          <Route path="/" element={<p>Contenido protegido</p>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  )
}

describe('RequireRole', () => {
  beforeEach(() => {
    useAuthStore.setState({ clinics: [], activeClinicId: null })
  })

  it('bloquea un rol que no esta en la lista', () => {
    useAuthStore.setState({
      clinics: [
        { clinic: { id: 'c1', name: 'Sucursal' }, role: { code: 'caja', name: 'Caja' } },
      ],
      activeClinicId: 'c1',
    })
    renderGuarded(['admin_clinica'])
    expect(screen.getByText('No tienes permiso para ver esta pantalla.')).toBeInTheDocument()
  })

  it('deja pasar un rol que si esta en la lista', () => {
    useAuthStore.setState({
      clinics: [
        {
          clinic: { id: 'c1', name: 'Sucursal' },
          role: { code: 'admin_clinica', name: 'Administrador' },
        },
      ],
      activeClinicId: 'c1',
    })
    renderGuarded(['admin_clinica'])
    expect(screen.getByText('Contenido protegido')).toBeInTheDocument()
  })

  it('la cuenta de demostracion (rol "demo") pasa cualquier guardia, aunque no este en la lista', () => {
    useAuthStore.setState({
      clinics: [
        {
          clinic: { id: 'c1', name: 'Clinica de demostracion' },
          role: { code: 'demo', name: 'Demostracion (temporal)' },
        },
      ],
      activeClinicId: 'c1',
    })
    renderGuarded(['admin_clinica'])
    expect(screen.getByText('Contenido protegido')).toBeInTheDocument()
  })
})
