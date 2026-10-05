import { describe, expect, it } from 'vitest'
import { canManageUsers } from './roles'

describe('canManageUsers', () => {
  it('permite a admin_clinica', () => {
    expect(canManageUsers('admin_clinica')).toBe(true)
  })

  it('permite a superadmin', () => {
    expect(canManageUsers('superadmin')).toBe(true)
  })

  it('no permite a odontologo', () => {
    expect(canManageUsers('odontologo')).toBe(false)
  })

  it('no permite cuando no hay rol activo', () => {
    expect(canManageUsers(null)).toBe(false)
  })
})
