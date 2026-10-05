import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { resolveApiAssetUrl } from '../api/client'
import { canConfigureAi, canManageBranding, canManageUsers, canReadAgenda } from '../modules/auth/roles'
import { useAuthStore } from '../modules/auth/store'
import { GlobalSearch } from '../modules/patients/GlobalSearch'
import { useGlobalSearchStore } from '../modules/patients/searchStore'
import { useThemeStore } from '../theme/store'
import styles from './Layout.module.css'

export function Layout() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const clinics = useAuthStore((s) => s.clinics)
  const activeClinicId = useAuthStore((s) => s.activeClinicId)
  const logout = useAuthStore((s) => s.logout)
  const branding = useThemeStore((s) => s.branding)
  const openSearch = useGlobalSearchStore((s) => s.setOpen)

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
          <li>
            <NavLink to="/pacientes" className={styles.navLink}>
              Pacientes
            </NavLink>
          </li>
          {canReadAgenda(activeRole) && (
            <li>
              <NavLink to="/agenda" className={styles.navLink}>
                Agenda
              </NavLink>
            </li>
          )}
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
          {canConfigureAi(activeRole) && (
            <li>
              <NavLink to="/configuracion/asistente-ia" className={styles.navLink}>
                Asistente IA
              </NavLink>
            </li>
          )}
        </ul>
      </aside>
      <header className={styles.header}>
        <button className={styles.searchButton} type="button" onClick={() => openSearch(true)}>
          Buscar paciente... <span>Ctrl+K</span>
        </button>
        <div className={styles.headerUser}>
          <span>{activeClinic?.clinic.name}</span>
          <span>{user?.full_name}</span>
          <button className={styles.logoutButton} type="button" onClick={handleLogout}>
            Salir
          </button>
        </div>
      </header>
      <main className={styles.content}>
        <Outlet />
      </main>
      <GlobalSearch />
    </div>
  )
}
