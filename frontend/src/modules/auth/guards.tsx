import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from './store'

export function RequireAuth() {
  const status = useAuthStore((s) => s.status)
  const user = useAuthStore((s) => s.user)
  const location = useLocation()

  if (status === 'checking') {
    return <p>Cargando...</p>
  }

  if (status === 'anonymous') {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  if (user?.mfa_setup_required && location.pathname !== '/configuracion/mfa') {
    return <Navigate to="/configuracion/mfa" replace />
  }

  return <Outlet />
}

export function RequireClinic() {
  const activeClinicId = useAuthStore((s) => s.activeClinicId)
  const clinics = useAuthStore((s) => s.clinics)

  if (!activeClinicId && clinics.length !== 1) {
    return <Navigate to="/seleccionar-sucursal" replace />
  }

  return <Outlet />
}

export function RequireRole({ roles }: { roles: string[] }) {
  const clinics = useAuthStore((s) => s.clinics)
  const activeClinicId = useAuthStore((s) => s.activeClinicId)
  const activeRole = clinics.find((c) => c.clinic.id === activeClinicId)?.role.code ?? null

  // Cuenta de demostracion de tiempo limitado (ver roles.ts::hasRole): unico rol
  // con todos los permisos, asi que tambien pasa cualquier guardia de ruta por
  // rol explicito, sin tener que repetirlo en cada `roles={[...]}` de router.tsx.
  const isDemoRole = activeRole === 'demo'

  if (!activeRole || (!isDemoRole && !roles.includes(activeRole))) {
    return <p>No tienes permiso para ver esta pantalla.</p>
  }

  return <Outlet />
}
