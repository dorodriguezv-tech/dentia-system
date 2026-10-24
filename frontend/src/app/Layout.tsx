import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { ClinicLogo, PoweredByDentia } from '../components/brand/Brand'
import {
  canConfigureAi,
  canConfigureBilling,
  canManageBranding,
  canManageCatalogs,
  canManageUsers,
  canReadAgenda,
  canReadReports,
  canUseVoice,
  canWriteBilling,
} from '../modules/auth/roles'
import { useAuthStore } from '../modules/auth/store'
import { useInactivityLogout } from '../modules/auth/useInactivityLogout'
import { GlobalSearch } from '../modules/patients/GlobalSearch'
import { useGlobalSearchStore } from '../modules/patients/searchStore'
import { DentiaOrb } from '../modules/voice/DentiaOrb'
import { useThemeStore } from '../theme/store'
import styles from './Layout.module.css'

export function Layout() {
  const navigate = useNavigate()
  useInactivityLogout()
  const user = useAuthStore((s) => s.user)
  const clinics = useAuthStore((s) => s.clinics)
  const activeClinicId = useAuthStore((s) => s.activeClinicId)
  const logout = useAuthStore((s) => s.logout)
  const branding = useThemeStore((s) => s.branding)
  const openSearch = useGlobalSearchStore((s) => s.setOpen)

  const activeClinic = clinics.find((c) => c.clinic.id === activeClinicId)
  const activeRole = activeClinic?.role.code ?? null
  const hasCustomLogo = branding?.has_custom_logo ?? false

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        {/* A7: logo (o nombre de la clinica, sin logo) arriba a la izquierda, visible
            en toda la app, que lleve a la pagina de inicio al hacer clic. */}
        <NavLink to="/" className={styles.brand}>
          <ClinicLogo
            logoUrl={branding?.logo_url ?? null}
            hasCustomLogo={hasCustomLogo}
            clinicName={branding?.display_name ?? 'DENT-IA'}
            width={160}
          />
        </NavLink>
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
          {canWriteBilling(activeRole) && (
            <li>
              <NavLink to="/caja" className={styles.navLink}>
                Caja
              </NavLink>
            </li>
          )}
          {canReadReports(activeRole) && (
            <li>
              <NavLink to="/reportes" className={styles.navLink}>
                Reportes
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
          {canConfigureAi(activeRole) && user?.ai_enabled && (
            <li>
              <NavLink to="/configuracion/asistente-ia" className={styles.navLink}>
                Asistente IA
              </NavLink>
            </li>
          )}
          {canConfigureBilling(activeRole) && (
            <li>
              <NavLink to="/configuracion/cobranza" className={styles.navLink}>
                Cobranza
              </NavLink>
            </li>
          )}
          {canManageCatalogs(activeRole) && (
            <li>
              <NavLink to="/configuracion/catalogos" className={styles.navLink}>
                Catalogos
              </NavLink>
            </li>
          )}
        </ul>
        {hasCustomLogo && (
          <div className={styles.sidebarFooter}>
            <PoweredByDentia />
          </div>
        )}
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
      {canUseVoice(activeRole) && user?.ai_enabled && <DentiaOrb />}
    </div>
  )
}
