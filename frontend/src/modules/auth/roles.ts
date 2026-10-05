/**
 * Copia minima, solo para la interfaz, del catalogo de roles de
 * backend/app/modules/iam/permissions_catalog.py (fuente de verdad real).
 * Si se agrega un rol nuevo ahi, se debe reflejar aqui.
 */
export const ROLES: { code: string; name: string }[] = [
  { code: 'admin_clinica', name: 'Administrador de la clinica' },
  { code: 'odontologo', name: 'Odontologo' },
  { code: 'especialista', name: 'Especialista' },
  { code: 'asistente', name: 'Asistente dental' },
  { code: 'recepcion', name: 'Recepcion' },
  { code: 'caja', name: 'Caja' },
]

/** Roles con el permiso `iam.manage_users` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_MANAGE_USERS = new Set(['superadmin', 'admin_clinica'])

export function canManageUsers(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_MANAGE_USERS.has(roleCode)
}
