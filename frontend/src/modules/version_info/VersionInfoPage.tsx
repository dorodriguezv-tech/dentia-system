import { useQuery } from '@tanstack/react-query'
import * as api from './api'
import styles from './VersionInfoPage.module.css'

const RELEASES_URL = 'https://github.com/dorodriguezv-tech/dentia-system/releases'

const ENVIRONMENT_LABELS: Record<string, string> = {
  production: 'Producción',
  development: 'Desarrollo',
}

function environmentLabel(environment: string): string {
  return ENVIRONMENT_LABELS[environment] ?? environment
}

export function VersionInfoPage() {
  const versionQuery = useQuery({
    queryKey: ['version-info'],
    queryFn: api.getVersionInfo,
  })

  return (
    <section>
      <h1>Control de versiones</h1>
      <p className={styles.description}>
        Esta pantalla muestra qué versión de DentalCare está corriendo en este
        servidor en este momento. Es solo informativa: actualizar a una
        versión nueva requiere acceso al servidor (lo hace una persona por
        SSH siguiendo el flujo de despliegue), no se puede hacer desde aquí.
      </p>

      {versionQuery.isLoading && <p>Cargando versión...</p>}
      {versionQuery.isError && (
        <p className={styles.errorBox}>No se pudo consultar la versión desplegada.</p>
      )}

      {versionQuery.data && (
        <div className={styles.panel}>
          <div className={styles.versionBlock}>
            <span className={styles.versionLabel}>Versión desplegada</span>
            <span className={styles.versionValue}>{versionQuery.data.version}</span>
          </div>
          <div className={styles.environmentBlock}>
            <span className={styles.environmentLabel}>Entorno</span>
            <span className={styles.environmentBadge}>
              {environmentLabel(versionQuery.data.environment)}
            </span>
          </div>
        </div>
      )}

      <div className={styles.releasesPanel}>
        <h2 className={styles.releasesTitle}>Historial de versiones</h2>
        <p className={styles.description}>
          El historial completo de versiones publicadas, con las notas de
          cada una, se consulta en GitHub (no se duplica aquí para no
          depender de una llamada a un servicio externo desde el servidor).
        </p>
        <a
          className={styles.releasesLink}
          href={RELEASES_URL}
          target="_blank"
          rel="noopener noreferrer"
        >
          Ver historial de versiones en GitHub ↗
        </a>
      </div>
    </section>
  )
}
