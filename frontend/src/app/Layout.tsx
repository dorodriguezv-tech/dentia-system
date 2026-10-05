import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { resolveApiAssetUrl } from '../api/client'
import { canManageBranding, canManageUsers } from '../modules/auth/roles'
import { useAuthStore } from '../modules/auth/store'
import { useThemeStore } from '../theme/store'
import styles from './Layout.module.css'

export function Layout() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const clinics = useAuthStore((s) => s.clinics)
  const activeClinicId = useAuthStore((s) => s.activeClinicId)
  const logout = useAuthStore((s) => s.logout)
  const branding = useThemeStore((s) => s.branding)

  const activeClinic = clinics.find((c) => c.clinic.id === activeClinicId)
  const activeRole = activeClinic?.role.code ?? null

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>
          {branding?.logo_url && (
            <img className={styles.brandLogo} src={resolveApiAssetUrl(branding.logo_url)} alt="" />
          )}
          {branding?.display_name ?? 'DentalCare'}
        </div>
        <ul className={styles.nav}>
          <li>
            <NavLink to="/" className={styles.navLink}>
              Inicio
            </NavLink>
          </li>
          {canManageUsers(activeRole) && (
            <li>
              <NavLink to="/usuarios" className={styles.navLink}>
                Usuarios
              </NavLink>
            </li>
          )}
          {canManageBranding(activeRole) && (
            <li>
              <NavLink to="/configuracion/apariencia" className={styles.navLink}>
                Apariencia
              </NavLink>
            </li>
          )}
        </ul>
      </aside>
      <header className={styles.header}>
        <strong>{activeClinic?.clinic.name ?? 'Sistema Clinico Dental'}</strong>
        <div className={styles.headerUser}>
          <span>{user?.full_name}</span>
          <button className={styles.logoutButton} type="button" onClick={handleLogout}>
            Salir
          </button>
        </div>
      </header>
      <main className={styles.content}>
        <Outlet />
      </main>
    </div>
  )
}
