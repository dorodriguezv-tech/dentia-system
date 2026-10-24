import { apiRequest } from '../../api/client'
import type {
  ClinicOut,
  ClinicUpdateInput,
  LoginResult,
  MfaSetupResponse,
  MyClinicOut,
  TokenResponse,
  UserOut,
} from './types'

export function login(
  email: string,
  password: string,
  turnstileToken: string | null,
): Promise<LoginResult> {
  return apiRequest<LoginResult>('/auth/login', {
    method: 'POST',
    body: { email, password, turnstile_token: turnstileToken },
    auth: false,
  })
}

export function loginMfa(mfaToken: string, code: string): Promise<TokenResponse> {
  return apiRequest<TokenResponse>('/auth/login/mfa', {
    method: 'POST',
    body: { mfa_token: mfaToken, code },
    auth: false,
  })
}

export function refresh(refreshToken: string): Promise<TokenResponse> {
  return apiRequest<TokenResponse>('/auth/refresh', {
    method: 'POST',
    body: { refresh_token: refreshToken },
    auth: false,
  })
}

export function logout(refreshToken: string): Promise<void> {
  return apiRequest<void>('/auth/logout', {
    method: 'POST',
    body: { refresh_token: refreshToken },
    auth: false,
  })
}

export function getMe(): Promise<UserOut> {
  return apiRequest<UserOut>('/me')
}

export function getMyClinics(): Promise<MyClinicOut[]> {
  return apiRequest<MyClinicOut[]>('/me/clinics')
}

// Pendiente de B1 (Parte B, Fase 12.2): editar los datos basicos de la propia
// sucursal desde Catalogos (nunca otra, no recibe un id en la URL).
export function updateCurrentClinic(input: ClinicUpdateInput): Promise<ClinicOut> {
  return apiRequest<ClinicOut>('/clinics/current', { method: 'PATCH', body: input })
}

export function setupMfa(): Promise<MfaSetupResponse> {
  return apiRequest<MfaSetupResponse>('/auth/mfa/setup', { method: 'POST' })
}

export function enableMfa(code: string): Promise<void> {
  return apiRequest<void>('/auth/mfa/enable', { method: 'POST', body: { code } })
}

export function disableMfa(code: string): Promise<void> {
  return apiRequest<void>('/auth/mfa/disable', { method: 'POST', body: { code } })
}
