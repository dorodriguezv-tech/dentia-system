import { useState } from 'react'
import { FINDING_CATALOG, FINDING_CODES } from './findingCatalog'
import styles from './FindingQuickMenu.module.css'
import { SURFACE_LABELS, validSurfacesForTooth } from './toothRules'
import type { FindingCode, Surface } from './types'

interface EncounterOption {
  id: string
  started_at: string
  chief_complaint: string | null
}

interface FindingQuickMenuProps {
  toothFdi: number
  initialSurface: Surface | null
  encounters: EncounterOption[]
  canWrite: boolean
  pending: boolean
  onClose: () => void
  onSubmit: (data: {
    encounter_id: string
    surface: Surface | null
    finding_code: FindingCode
    material: string | null
  }) => void
}

export function FindingQuickMenu({
  toothFdi,
  initialSurface,
  encounters,
  canWrite,
  pending,
  onClose,
  onSubmit,
}: FindingQuickMenuProps) {
  const [surface, setSurface] = useState<Surface | null>(initialSurface)
  const [findingCode, setFindingCode] = useState<FindingCode | null>(null)
  const [material, setMaterial] = useState('')
  const [encounterId, setEncounterId] = useState('')

  const surfaces = validSurfacesForTooth(toothFdi)

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h3>Pieza {toothFdi}</h3>
        <button className={styles.closeButton} type="button" onClick={onClose}>
          Cerrar
        </button>
      </div>

      {canWrite ? (
        <>
          <div className={styles.surfaceRow}>
            {surfaces.map((s) => (
              <button
                key={s}
                type="button"
                className={surface === s ? styles.surfaceChipActive : styles.surfaceChip}
                onClick={() => setSurface(s)}
              >
                {SURFACE_LABELS[s]}
              </button>
            ))}
            <button
              type="button"
              className={surface === null ? styles.surfaceChipActive : styles.surfaceChip}
              onClick={() => setSurface(null)}
            >
              Toda la pieza
            </button>
          </div>

          <select value={encounterId} onChange={(e) => setEncounterId(e.target.value)}>
            <option value="">Selecciona una atencion...</option>
            {encounters.map((encounter) => (
              <option key={encounter.id} value={encounter.id}>
                {new Date(encounter.started_at).toLocaleDateString('es-MX')} —{' '}
                {encounter.chief_complaint ?? 'Sin motivo'}
              </option>
            ))}
          </select>

          <div className={styles.findingGrid}>
            {FINDING_CODES.map((code) => (
              <button
                key={code}
                type="button"
                className={findingCode === code ? styles.findingButtonActive : styles.findingButton}
                style={{ borderColor: FINDING_CATALOG[code].color }}
                onClick={() => setFindingCode(code)}
              >
                <span className={styles.swatch} style={{ backgroundColor: FINDING_CATALOG[code].color }} />
                {FINDING_CATALOG[code].label}
              </button>
            ))}
          </div>

          <input
            type="text"
            placeholder="Material (opcional)"
            value={material}
            onChange={(e) => setMaterial(e.target.value)}
          />

          <button
            className={styles.submitButton}
            type="button"
            disabled={!encounterId || !findingCode || pending}
            onClick={() =>
              findingCode &&
              onSubmit({
                encounter_id: encounterId,
                surface,
                finding_code: findingCode,
                material: material || null,
              })
            }
          >
            {pending ? 'Guardando...' : 'Registrar hallazgo'}
          </button>
        </>
      ) : (
        <p>No tienes permiso para editar el odontograma.</p>
      )}
    </div>
  )
}
