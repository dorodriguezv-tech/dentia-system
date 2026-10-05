import { NavLink, Outlet } from 'react-router-dom'
import styles from './Layout.module.css'

const NAV_ITEMS = [{ to: '/', label: 'Inicio' }]

export function Layout() {
  return (
    <div className={styles.shell}>
      <aside className={styles.sidebar}>
        <div className={styles.brand}>DentalCare</div>
        <ul className={styles.nav}>
          {NAV_ITEMS.map((item) => (
            <li key={item.to}>
              <NavLink to={item.to} className={styles.navLink}>
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </aside>
      <header className={styles.header}>
        <strong>Sistema Clinico Dental</strong>
      </header>
      <main className={styles.content}>
        <Outlet />
      </main>
    </div>
  )
}
