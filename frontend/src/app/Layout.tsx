import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { apiRequestBlobUrl } from '../api/client'
import { ClinicLogo, PoweredByDentia } from '../components/brand/Brand'
import { EnSalaAlert } from '../modules/agenda/EnSalaAlert'
import {
  canConfigureAi,
  canConfigureBilling,
  canManageBranding,
  canManageCatalogs,
  canManageDocumentSettings,
  canManageUsers,
  canManageWorkingHours,
  canReadAgenda,
  canReadReports,
  canUseVoice,
  canViewVersionInfo,
  canWriteBilling,
} from '../modules/auth/roles'
import { useAuthStore } from '../modules/auth/store'
import { useInactivityLogout } from '../modules/auth/useInactivityLogout'
import { GlobalSearch } from '../modules/patients/GlobalSearch'
import { useGlobalSearchStore } from '../modules/patients/searchStore'
import { DentiaOrb } from '../modules/voice/DentiaOrb'
import { useThemeStore } from '../theme/store'
import styles from './Layout.module.css'

// Igual que patients/PatientHeader.tsx::usePhotoUrl -- un <img src> directo no puede
// mandar el Authorization header, asi que hay que pedir el archivo con fetch
// autenticado y convertirlo a blob URL.
function useOwnPhotoUrl(userId: string | undefined, hasPhoto: boolean | undefined): string | null {
  const [url, setUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!userId || !hasPhoto) return

    let objectUrl: string | null = null
    let cancelled = false
    apiRequestBlobUrl(`/users/${userId}/photo`).then((u) => {
      if (cancelled) {
        URL.revokeObjectURL(u)
        return
      }
      objectUrl = u
      setUrl(u)
    })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [userId, hasPhoto])

  return url
}

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
  const ownPhotoUrl = useOwnPhotoUrl(user?.id, user?.has_photo)

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
          {/* Titulo de la clinica, siempre visible (no solo con logo propio) --
              el logo generico de DENT-IA no menciona el nombre de la clinica. */}
          {branding?.display_name && (
            <span className={styles.clinicName} aria-hidden="true">
              {branding.display_name}
            </span>
          )}
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
          {canManageDocumentSettings(activeRole) && (
            <li>
              <NavLink to="/configuracion/formatos-documentos" className={styles.navLink}>
                Formatos de documentos
              </NavLink>
            </li>
          )}
          {canViewVersionInfo(activeRole) && (
            <li>
              <NavLink to="/configuracion/version" className={styles.navLink}>
                Control de versiones
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
          {canManageWorkingHours(activeRole) && (
            <li>
              <NavLink to="/configuracion/horarios" className={styles.navLink}>
                Horarios
              </NavLink>
            </li>
          )}
          <li>
            <NavLink to="/ayuda" className={styles.navLink}>
              Ayuda
            </NavLink>
          </li>
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
          {ownPhotoUrl && <img className={styles.ownPhoto} src={ownPhotoUrl} alt="" />}
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
      <EnSalaAlert />
      {canUseVoice(activeRole) && user?.ai_enabled && <DentiaOrb />}
    </div>
  )
}
