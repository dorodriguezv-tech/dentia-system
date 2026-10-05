import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as encountersApi from '../encounters/api'
import * as api from './api'
import { Arch } from './Arch'
import { FINDING_CATALOG, FINDING_CODES } from './findingCatalog'
import { FindingQuickMenu } from './FindingQuickMenu'
import styles from './Odontograma.module.css'
import { ToothHistoryPanel } from './ToothHistoryPanel'
import {
  LOWER_PERMANENT_ROW,
  LOWER_TEMPORARY_ROW,
  UPPER_PERMANENT_ROW,
  UPPER_TEMPORARY_ROW,
} from './toothRules'
import type { Surface, ToothFindingOut, ViewMode } from './types'

const VIEW_LABELS: Record<ViewMode, string> = {
  permanente: 'Permanente',
  temporal: 'Temporal',
  mixta: 'Mixta',
}

export function Odontograma({ patientId, canWrite }: { patientId: string; canWrite: boolean }) {
  const queryClient = useQueryClient()
  const [viewMode, setViewMode] = useState<ViewMode>('permanente')
  const [atDate, setAtDate] = useState('')
  const [selected, setSelected] = useState<{ tooth: number; surface: Surface | null } | null>(null)

  const odontogramQuery = useQuery({
    queryKey: ['odontogram', patientId, atDate],
    queryFn: () => api.getOdontogram(patientId, atDate || undefined),
  })
  const encountersQuery = useQuery({
    queryKey: ['patient-encounters', patientId],
    queryFn: () => encountersApi.listPatientEncounters(patientId),
  })

  const findingsByTooth = useMemo(() => {
    const map = new Map<number, ToothFindingOut[]>()
    for (const finding of odontogramQuery.data ?? []) {
      const list = map.get(finding.tooth_fdi) ?? []
      list.push(finding)
      map.set(finding.tooth_fdi, list)
    }
    return map
  }, [odontogramQuery.data])

  const createMutation = useMutation({
    mutationFn: api.createToothFinding,
    onSuccess: (_result, variables) => {
      queryClient.invalidateQueries({ queryKey: ['odontogram', patientId] })
      queryClient.invalidateQueries({
        queryKey: ['tooth-history', patientId, variables.tooth_fdi],
      })
      setSelected(null)
    },
  })

  const isPastView = atDate !== ''

  function handleSurfaceClick(tooth: number, surface: Surface | null) {
    setSelected({ tooth, surface })
  }

  return (
    <div className={styles.wrapper}>
      <div className={styles.controls}>
        <div className={styles.viewToggle}>
          {(Object.keys(VIEW_LABELS) as ViewMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              className={viewMode === mode ? styles.viewButtonActive : styles.viewButton}
              onClick={() => setViewMode(mode)}
            >
              {VIEW_LABELS[mode]}
            </button>
          ))}
        </div>

        <label className={styles.dateSlider}>
          Historial a fecha
          <input
            type="date"
            value={atDate}
            max={new Date().toISOString().slice(0, 10)}
            onChange={(e) => setAtDate(e.target.value)}
          />
        </label>
        {isPastView && (
          <button type="button" className={styles.todayButton} onClick={() => setAtDate('')}>
            Volver a hoy
          </button>
        )}
      </div>

      {isPastView && (
        <div className={styles.pastBanner}>
          Viendo el odontograma al {new Date(`${atDate}T00:00:00`).toLocaleDateString('es-MX')}.
          Solo lectura.
        </div>
      )}

      <div className={styles.archContainer}>
        {viewMode !== 'permanente' && (
          <>
            {viewMode === 'mixta' && <p className={styles.rowLabel}>Temporales</p>}
            <Arch
              teeth={UPPER_TEMPORARY_ROW}
              findingsByTooth={findingsByTooth}
              small={viewMode === 'mixta'}
              selectedTooth={selected?.tooth ?? null}
              onSurfaceClick={handleSurfaceClick}
            />
          </>
        )}
        {viewMode !== 'temporal' && (
          <>
            {viewMode === 'mixta' && <p className={styles.rowLabel}>Permanentes</p>}
            <Arch
              teeth={UPPER_PERMANENT_ROW}
              findingsByTooth={findingsByTooth}
              selectedTooth={selected?.tooth ?? null}
              onSurfaceClick={handleSurfaceClick}
            />
          </>
        )}

        <div className={styles.midline} />

        {viewMode !== 'temporal' && (
          <Arch
            teeth={LOWER_PERMANENT_ROW}
            findingsByTooth={findingsByTooth}
            selectedTooth={selected?.tooth ?? null}
            onSurfaceClick={handleSurfaceClick}
          />
        )}
        {viewMode !== 'permanente' && (
          <Arch
            teeth={LOWER_TEMPORARY_ROW}
            findingsByTooth={findingsByTooth}
            small={viewMode === 'mixta'}
            selectedTooth={selected?.tooth ?? null}
            onSurfaceClick={handleSurfaceClick}
          />
        )}
      </div>

      <div className={styles.legend}>
        {FINDING_CODES.map((code) => (
          <span key={code} className={styles.legendItem}>
            <span
              className={styles.legendSwatch}
              style={{ backgroundColor: FINDING_CATALOG[code].color }}
            />
            {FINDING_CATALOG[code].label}
          </span>
        ))}
      </div>

      {selected && (
        <div className={styles.sidePanels}>
          {!isPastView && (
            <FindingQuickMenu
              toothFdi={selected.tooth}
              initialSurface={selected.surface}
              encounters={encountersQuery.data ?? []}
              canWrite={canWrite}
              pending={createMutation.isPending}
              onClose={() => setSelected(null)}
              onSubmit={(data) =>
                createMutation.mutate({
                  patient_id: patientId,
                  tooth_fdi: selected.tooth,
                  ...data,
                })
              }
            />
          )}
          <ToothHistoryPanel patientId={patientId} toothFdi={selected.tooth} />
        </div>
      )}
    </div>
  )
}
