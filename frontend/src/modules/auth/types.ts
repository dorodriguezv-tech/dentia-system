export interface UserOut {
  id: string
  email: string
  full_name: string
  is_active: boolean
  mfa_enabled: boolean
  mfa_setup_required: boolean
}

export interface RoleOut {
  code: string
  name: string
}

export interface ClinicOut {
  id: string
  name: string
  // Opcionales en el tipo (el backend siempre los manda, aunque sea null) para no
  // obligar a cada fixture de prueba que ya construye un MyClinicOut a incluirlos.
  address?: string | null
  phone?: string | null
  // Bug #42 de docs/PENDIENTES_CLINICOS.md: zona horaria IANA de la sucursal,
  // usada por el backend para calcular "hoy" en citas/atenciones.
  timezone?: string
}

export interface ClinicUpdateInput {
  name?: string
  address?: string
  phone?: string
  timezone?: string
}

export interface MyClinicOut {
  clinic: ClinicOut
  role: RoleOut
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: UserOut
}

export interface MfaRequiredResponse {
  mfa_required: true
  mfa_token: string
}

export type LoginResult = TokenResponse | MfaRequiredResponse

export function isMfaRequired(result: LoginResult): result is MfaRequiredResponse {
  return 'mfa_required' in result
}

export interface MfaSetupResponse {
  secret: string
  otpauth_url: string
}

export interface UserWithRoleOut {
  user: UserOut
  role: RoleOut
}
