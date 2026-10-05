import type { MyClinicOut, UserOut } from './types'

/** A donde mandar al usuario justo despues de autenticarse. */
export function postLoginRedirect(user: UserOut | null, clinics: MyClinicOut[]): string {
  if (user?.mfa_setup_required) return '/configuracion/mfa'
  if (clinics.length > 1) return '/seleccionar-sucursal'
  return '/'
}
