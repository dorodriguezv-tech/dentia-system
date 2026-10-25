import { describe, expect, it } from 'vitest'
import {
  canManageBranding,
  canManageCatalogs,
  canManageUsers,
  canReadAgenda,
  canReadBilling,
  canWriteRecords,
} from './roles'

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

// Cuenta de demostracion de tiempo limitado (backend: rol "demo", todos los
// permisos del catalogo) -- debe pasar CUALQUIER funcion can*(), sin importar
// que tan restringido este ese permiso para los demas roles.
describe('rol "demo" (cuenta de demostracion)', () => {
  it('pasa funciones muy abiertas (varios roles)', () => {
    expect(canReadAgenda('demo')).toBe(true)
  })

  it('pasa funciones de un solo rol (admin_clinica)', () => {
    expect(canManageUsers('demo')).toBe(true)
    expect(canManageBranding('demo')).toBe(true)
    expect(canManageCatalogs('demo')).toBe(true)
    expect(canReadBilling('demo')).toBe(true)
  })

  it('pasa funciones clinicas (odontologo/especialista)', () => {
    expect(canWriteRecords('demo')).toBe(true)
  })
})
