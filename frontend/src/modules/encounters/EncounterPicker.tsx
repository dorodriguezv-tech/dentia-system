import type { EncounterOut } from './types'
import type { EncounterPicker } from './useEncounterPicker'
import styles from './EncounterPicker.module.css'

const NEW_ENCOUNTER_OPTION = '__nueva_atencion__'

function EncounterSelect({
  encounters,
  value,
  onChange,
  canCreateNew,
  onCreateNew,
  isCreating,
}: {
  encounters: Pick<EncounterOut, 'id' | 'started_at' | 'chief_complaint'>[]
  value: string
  onChange: (encounterId: string) => void
  canCreateNew: boolean
  onCreateNew: () => void
  isCreating: boolean
}) {
  return (
    <select
      aria-label="Atencion"
      value={value}
      disabled={isCreating}
      onChange={(e) => {
        if (e.target.value === NEW_ENCOUNTER_OPTION) {
          onCreateNew()
          return
        }
        onChange(e.target.value)
      }}
    >
      <option value="">Selecciona una atencion...</option>
      {encounters.map((encounter) => (
        <option key={encounter.id} value={encounter.id}>
          {new Date(encounter.started_at).toLocaleDateString('es-MX')} —{' '}
          {encounter.chief_complaint ?? 'Sin motivo'}
        </option>
      ))}
      {canCreateNew && (
        <option value={NEW_ENCOUNTER_OPTION}>
          {isCreating ? 'Iniciando atencion...' : '+ Iniciar atencion nueva'}
        </option>
      )}
    </select>
  )
}

/** A3: el selector nunca se queda vacio en silencio -- si la carga de atenciones o la
 * creacion de una nueva fallan, el error se ve junto al selector. */
export function EncounterPickerField({ encounterPicker }: { encounterPicker: EncounterPicker }) {
  return (
    <>
      <EncounterSelect
        encounters={encounterPicker.encounters}
        value={encounterPicker.encounterId}
        onChange={encounterPicker.setEncounterId}
        canCreateNew={encounterPicker.canCreateNew}
        onCreateNew={encounterPicker.createNew}
        isCreating={encounterPicker.isCreating}
      />
      {encounterPicker.loadError && (
        <span className={styles.errorBox}>No se pudieron cargar las atenciones del paciente.</span>
      )}
      {encounterPicker.createError && (
        <span className={styles.errorBox}>No se pudo iniciar la atencion nueva.</span>
      )}
    </>
  )
}
