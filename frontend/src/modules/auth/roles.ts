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

// Cuenta de demostracion de tiempo limitado (backend/app/modules/iam/permissions_catalog.py):
// unico rol con TODOS los permisos -- en vez de repetir 'demo' en cada uno de los
// Set de abajo (fuente real de desincronizacion si se olvida uno), toda funcion
// can*() de este archivo pasa por este helper.
const DEMO_ROLE_CODE = 'demo'

function hasRole(roleCode: string | null, allowed: Set<string>): boolean {
  return roleCode !== null && (roleCode === DEMO_ROLE_CODE || allowed.has(roleCode))
}

/** Roles con el permiso `iam.manage_users` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_MANAGE_USERS = new Set(['superadmin', 'admin_clinica'])

export function canManageUsers(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_MANAGE_USERS)
}

/** Roles con el permiso `branding.manage` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_MANAGE_BRANDING = new Set(['superadmin', 'admin_clinica'])

export function canManageBranding(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_MANAGE_BRANDING)
}

/** Roles con el permiso `document_settings.manage` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_MANAGE_DOCUMENT_SETTINGS = new Set(['superadmin', 'admin_clinica'])

export function canManageDocumentSettings(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_MANAGE_DOCUMENT_SETTINGS)
}

/** Roles con el permiso `version_info.read` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_VIEW_VERSION_INFO = new Set(['superadmin', 'admin_clinica'])

export function canViewVersionInfo(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_VIEW_VERSION_INFO)
}

/** Roles con el permiso `patients.write` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_WRITE_PATIENTS = new Set(['admin_clinica', 'recepcion', 'odontologo'])

export function canWritePatients(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_WRITE_PATIENTS)
}

/** Roles con el permiso `records.write` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_WRITE_RECORDS = new Set(['odontologo', 'especialista'])

export function canWriteRecords(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_WRITE_RECORDS)
}

/** Roles con el permiso `records.read` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_READ_RECORDS = new Set(['odontologo', 'especialista'])

export function canReadRecords(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_READ_RECORDS)
}

/** Roles con el permiso `odontogram.write` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_WRITE_ODONTOGRAM = new Set(['odontologo', 'especialista'])

export function canWriteOdontogram(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_WRITE_ODONTOGRAM)
}

/** Roles con el permiso `odontogram.read` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_READ_ODONTOGRAM = new Set(['odontologo', 'especialista', 'asistente'])

export function canReadOdontogram(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_READ_ODONTOGRAM)
}

/** Roles con el permiso `agenda.write` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_WRITE_AGENDA = new Set([
  'admin_clinica',
  'odontologo',
  'especialista',
  'recepcion',
])

export function canWriteAgenda(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_WRITE_AGENDA)
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
  return hasRole(roleCode, ROLES_THAT_READ_AGENDA)
}

/** Roles con los permisos `diagnosis.write`/`diagnosis.read` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_WRITE_DIAGNOSIS = new Set(['odontologo', 'especialista'])
const ROLES_THAT_READ_DIAGNOSIS = new Set(['odontologo', 'especialista'])

export function canWriteDiagnosis(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_WRITE_DIAGNOSIS)
}

export function canReadDiagnosis(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_READ_DIAGNOSIS)
}

/** Roles con los permisos `treatment.*` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_WRITE_TREATMENT = new Set(['odontologo', 'especialista'])
const ROLES_THAT_READ_TREATMENT = new Set(['admin_clinica', 'odontologo', 'especialista'])
const ROLES_THAT_ACCEPT_BUDGET = new Set(['odontologo', 'especialista'])

export function canWriteTreatment(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_WRITE_TREATMENT)
}

export function canReadTreatment(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_READ_TREATMENT)
}

export function canAcceptBudget(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_ACCEPT_BUDGET)
}

/** Roles con los permisos `ai.use`/`ai.configure` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_USE_AI = new Set(['odontologo', 'especialista'])
const ROLES_THAT_CONFIGURE_AI = new Set(['admin_clinica'])

export function canUseAi(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_USE_AI)
}

export function canConfigureAi(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_CONFIGURE_AI)
}

/** Roles con los permisos `documents.*` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_READ_DOCUMENTS = new Set(['admin_clinica', 'odontologo', 'especialista'])
const ROLES_THAT_WRITE_DOCUMENTS = new Set(['odontologo', 'especialista'])
const ROLES_THAT_SIGN_DOCUMENTS = new Set(['odontologo', 'especialista'])

export function canReadDocuments(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_READ_DOCUMENTS)
}

export function canWriteDocuments(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_WRITE_DOCUMENTS)
}

export function canSignDocuments(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_SIGN_DOCUMENTS)
}

/** Roles con los permisos `imaging.*` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_READ_IMAGING = new Set(['odontologo', 'especialista', 'asistente'])
const ROLES_THAT_WRITE_IMAGING = new Set(['odontologo', 'especialista', 'asistente'])

export function canReadImaging(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_READ_IMAGING)
}

export function canWriteImaging(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_WRITE_IMAGING)
}

/** Roles con los permisos `billing.*` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_READ_BILLING = new Set(['admin_clinica', 'recepcion', 'caja'])
const ROLES_THAT_WRITE_BILLING = new Set(['admin_clinica', 'caja'])
const ROLES_THAT_CONFIGURE_BILLING = new Set(['admin_clinica'])

export function canReadBilling(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_READ_BILLING)
}

export function canWriteBilling(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_WRITE_BILLING)
}

export function canConfigureBilling(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_CONFIGURE_BILLING)
}

/** Roles con el permiso `reports.read` (ver docs/MATRIZ_PERMISOS.md). */
const ROLES_THAT_READ_REPORTS = new Set(['superadmin', 'admin_clinica', 'caja'])

export function canReadReports(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_READ_REPORTS)
}

/** Roles con el permiso `catalogs.manage` (ver docs/MATRIZ_PERMISOS.md). Solo
 * admin_clinica a proposito: superadmin no tiene acceso a datos clinicos (CLAUDE.md
 * sec. 5) y varios de estos catalogos lo son (hallazgos, diagnosticos...). */
const ROLES_THAT_MANAGE_CATALOGS = new Set(['admin_clinica'])

export function canManageCatalogs(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_MANAGE_CATALOGS)
}

/** Roles con el permiso `voice.use` (ver docs/MATRIZ_PERMISOS.md) -- Fase 13
 * ("Dentia"). odontologo/especialista tienen ademas `voice.clinical`, pero esa
 * distincion solo le importa al backend al decidir que intenciones ofrecer
 * (docs/06_INSTRUCCIONES... sec. C1); el frontend solo necesita saber si debe
 * mostrar el orbe. */
const ROLES_THAT_USE_VOICE = new Set(['odontologo', 'especialista', 'recepcion'])

export function canUseVoice(roleCode: string | null): boolean {
  return hasRole(roleCode, ROLES_THAT_USE_VOICE)
}
