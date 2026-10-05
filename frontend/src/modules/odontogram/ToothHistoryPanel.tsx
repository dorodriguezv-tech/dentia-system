import { useQuery } from '@tanstack/react-query'
import * as api from './api'
import { FINDING_CATALOG } from './findingCatalog'
import styles from './FindingQuickMenu.module.css'
import historyStyles from './ToothHistoryPanel.module.css'
import { SURFACE_LABELS } from './toothRules'

export function ToothHistoryPanel({ patientId, toothFdi }: { patientId: string; toothFdi: number }) {
  const historyQuery = useQuery({
    queryKey: ['tooth-history', patientId, toothFdi],
    queryFn: () => api.getToothHistory(patientId, toothFdi),
  })

  return (
    <div className={styles.panel}>
      <h3>Historial de la pieza {toothFdi}</h3>
      {historyQuery.isLoading && <p>Cargando...</p>}
      {historyQuery.data?.length === 0 && <p>Sin eventos registrados para esta pieza.</p>}
      {historyQuery.data?.map((entry) => (
        <div
          key={entry.id}
          className={entry.is_current ? historyStyles.entryCurrent : historyStyles.entry}
        >
          <strong>{FINDING_CATALOG[entry.finding_code].label}</strong>{' '}
          {entry.surface ? `(${SURFACE_LABELS[entry.surface]})` : '(toda la pieza)'}
          {entry.material && ` — ${entry.material}`}
          <div className={historyStyles.meta}>
            {new Date(entry.created_at).toLocaleString('es-MX')} · {entry.author_name || 'Sin autor'}
            {entry.is_current ? ' · vigente' : ' · reemplazado'}
          </div>
        </div>
      ))}
    </div>
  )
}
