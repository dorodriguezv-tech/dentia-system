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

/** Roles con el permiso `branding.manage` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_MANAGE_BRANDING = new Set(['superadmin', 'admin_clinica'])

export function canManageBranding(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_MANAGE_BRANDING.has(roleCode)
}

/** Roles con el permiso `patients.write` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_WRITE_PATIENTS = new Set(['admin_clinica', 'recepcion'])

export function canWritePatients(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_WRITE_PATIENTS.has(roleCode)
}

/** Roles con el permiso `records.write` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_WRITE_RECORDS = new Set(['odontologo', 'especialista'])

export function canWriteRecords(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_WRITE_RECORDS.has(roleCode)
}

/** Roles con el permiso `records.read` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_READ_RECORDS = new Set(['odontologo', 'especialista'])

export function canReadRecords(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_READ_RECORDS.has(roleCode)
}

/** Roles con el permiso `odontogram.write` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_WRITE_ODONTOGRAM = new Set(['odontologo', 'especialista'])

export function canWriteOdontogram(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_WRITE_ODONTOGRAM.has(roleCode)
}

/** Roles con el permiso `odontogram.read` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_READ_ODONTOGRAM = new Set(['odontologo', 'especialista', 'asistente'])

export function canReadOdontogram(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_READ_ODONTOGRAM.has(roleCode)
}

/** Roles con el permiso `agenda.write` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_WRITE_AGENDA = new Set(['admin_clinica', 'odontologo', 'especialista', 'recepcion'])

export function canWriteAgenda(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_WRITE_AGENDA.has(roleCode)
}

/** Roles con el permiso `agenda.read` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_READ_AGENDA = new Set([
  'admin_clinica',
  'odontologo',
  'especialista',
  'asistente',
  'recepcion',
])

export function canReadAgenda(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_READ_AGENDA.has(roleCode)
}

/** Roles con los permisos `diagnosis.write`/`diagnosis.read` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_WRITE_DIAGNOSIS = new Set(['odontologo', 'especialista'])
const ROLES_THAT_READ_DIAGNOSIS = new Set(['odontologo', 'especialista'])

export function canWriteDiagnosis(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_WRITE_DIAGNOSIS.has(roleCode)
}

export function canReadDiagnosis(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_READ_DIAGNOSIS.has(roleCode)
}

/** Roles con los permisos `treatment.*` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_WRITE_TREATMENT = new Set(['odontologo', 'especialista'])
const ROLES_THAT_READ_TREATMENT = new Set(['admin_clinica', 'odontologo', 'especialista'])
const ROLES_THAT_ACCEPT_BUDGET = new Set(['odontologo', 'especialista'])

export function canWriteTreatment(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_WRITE_TREATMENT.has(roleCode)
}

export function canReadTreatment(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_READ_TREATMENT.has(roleCode)
}

export function canAcceptBudget(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_ACCEPT_BUDGET.has(roleCode)
}

/** Roles con los permisos `ai.use`/`ai.configure` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_USE_AI = new Set(['odontologo', 'especialista'])
const ROLES_THAT_CONFIGURE_AI = new Set(['admin_clinica'])

export function canUseAi(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_USE_AI.has(roleCode)
}

export function canConfigureAi(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_CONFIGURE_AI.has(roleCode)
}

/** Roles con los permisos `documents.*` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_READ_DOCUMENTS = new Set(['admin_clinica', 'odontologo', 'especialista'])
const ROLES_THAT_WRITE_DOCUMENTS = new Set(['odontologo', 'especialista'])
const ROLES_THAT_SIGN_DOCUMENTS = new Set(['odontologo', 'especialista'])

export function canReadDocuments(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_READ_DOCUMENTS.has(roleCode)
}

export function canWriteDocuments(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_WRITE_DOCUMENTS.has(roleCode)
}

export function canSignDocuments(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_SIGN_DOCUMENTS.has(roleCode)
}

/** Roles con los permisos `imaging.*` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_READ_IMAGING = new Set(['odontologo', 'especialista', 'asistente'])
const ROLES_THAT_WRITE_IMAGING = new Set(['odontologo', 'especialista', 'asistente'])

export function canReadImaging(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_READ_IMAGING.has(roleCode)
}

export function canWriteImaging(roleCode: string | null): boolean {
  return roleCode !== null && ROLES_THAT_WRITE_IMAGING.has(roleCode)
}
