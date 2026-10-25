import { describe, expect, it } from 'vitest'
import { postLoginRedirect } from './navigation'
import type { MyClinicOut, UserOut } from './types'

const baseUser: UserOut = {
  id: '1',
  email: 'a@example.com',
  full_name: 'Usuario',
  professional_license: null,
  is_active: true,
  mfa_enabled: false,
  mfa_setup_required: false,
  ai_enabled: true,
  has_photo: false,
}

const clinic: MyClinicOut = {
  clinic: { id: 'c1', name: 'Sucursal Centro' },
  role: { code: 'odontologo', name: 'Odontologo' },
}

describe('postLoginRedirect', () => {
  it('manda a configurar MFA si el rol lo exige y no esta activa', () => {
    const user = { ...baseUser, mfa_setup_required: true }
    expect(postLoginRedirect(user, [clinic])).toBe('/configuracion/mfa')
  })

  it('manda a elegir sucursal si tiene mas de una', () => {
    expect(postLoginRedirect(baseUser, [clinic, clinic])).toBe('/seleccionar-sucursal')
  })

  it('manda al inicio si solo tiene una sucursal y no necesita MFA', () => {
    expect(postLoginRedirect(baseUser, [clinic])).toBe('/')
  })
})
