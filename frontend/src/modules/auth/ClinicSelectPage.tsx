import { useNavigate } from 'react-router-dom'
import styles from './AuthForm.module.css'
import { useAuthStore } from './store'

export function ClinicSelectPage() {
  const navigate = useNavigate()
  const clinics = useAuthStore((s) => s.clinics)
  const selectClinic = useAuthStore((s) => s.selectClinic)

  function handleSelect(clinicId: string) {
    selectClinic(clinicId)
    navigate('/')
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <p className={styles.brand}>Elige tu sucursal</p>
        <div className={styles.clinicList}>
          {clinics.map(({ clinic, role }) => (
            <button
              key={clinic.id}
              className={styles.clinicButton}
              type="button"
              onClick={() => handleSelect(clinic.id)}
            >
              <strong>{clinic.name}</strong>
              <div>{role.name}</div>
            </button>
          ))}
        </div>
        {clinics.length === 0 && (
          <p className={styles.hint}>No tienes sucursales asignadas. Contacta al administrador.</p>
        )}
      </div>
    </div>
  )
}
