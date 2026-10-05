import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { canManageUsers } from '../modules/auth/roles'
import { useAuthStore } from '../modules/auth/store'
import styles from './Layout.module.css'

export function Layout() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const clinics = useAuthStore((s) => s.clinics)
  const activeClinicId = useAuthStore((s) => s.activeClinicId)
  const logout = useAuthStore((s) => s.logout)

  const activeClinic = clinics.find((c) => c.clinic.id === activeClinicId)

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>DentalCare</div>
        <ul className={styles.nav}>
          <li>
            <NavLink to="/" className={styles.navLink}>
              Inicio
            </NavLink>
          </li>
          {canManageUsers(activeClinic?.role.code ?? null) && (
            <li>
              <NavLink to="/usuarios" className={styles.navLink}>
                Usuarios
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
