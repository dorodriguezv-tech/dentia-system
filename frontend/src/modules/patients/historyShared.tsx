import { useState } from 'react'
import styles from './PatientDetailPage.module.css'

/** Piezas de UI compartidas entre las sub-pestanas de Historia Clinica (General
 * en ExpedienteTab.tsx, Odontologica en OdontologicalHistoryTab.tsx, y las que
 * sigan) -- evita duplicar el mismo patron de "ya guardado"/anulacion/badge en
 * cada archivo nuevo. Extraido de ExpedienteTab.tsx (Fase A) sin cambios de
 * comportamiento.
 */

export function AnnulButton({ onAnnul }: { onAnnul: (reason: string) => void }) {
  const [reason, setReason] = useState('')
  const [open, setOpen] = useState(false)

  if (!open) {
    return (
      <button className={styles.linkButton} type="button" onClick={() => setOpen(true)}>
        Anular
      </button>
    )
  }

  return (
    <span>
      <input
        type="text"
        placeholder="Motivo de anulacion"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
      />
      <button
        className={styles.linkButton}
        type="button"
        disabled={!reason.trim()}
        onClick={() => onAnnul(reason)}
      >
        Confirmar
      </button>
    </span>
  )
}

/** Correccion Fase A: indicador breve junto al <summary> cuando la seccion
 * tiene cero entradas activas para este paciente -- desaparece en cuanto haya
 * al menos una. No valida campo por campo, solo "0 entradas activas". */
export function MissingDataBadge({ hasActiveEntries }: { hasActiveEntries: boolean }) {
  if (hasActiveEntries) return null
  return <span className={styles.missingBadge}>Faltan datos</span>
}

/** Correccion Fase A: vista detallada tipo "lista de definiciones" (como
 * DatosGeneralesSection) para una entrada ya guardada -- reemplaza los
 * resumenes de una sola linea que omitian la mayoria de los campos
 * capturados. Solo muestra filas con un valor presente (no vacio/false). */
export function DetailList({ rows }: { rows: [string, string][] }) {
  if (rows.length === 0) return <p>Sin datos relevantes.</p>
  return (
    <dl className={styles.entryDetail}>
      {rows.map(([label, value]) => (
        <div key={label} className={styles.infoRow}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  )
}

/** Fase E (Historia Clinica Pediatrica): varios campos del backend son
 * `bool | null` con tres estados reales (sin responder / si / no) en vez de
 * dos -- un checkbox no puede representar "sin responder" distinto de
 * "false", asi que se usan 3 radios mutuamente excluyentes por campo. Vive
 * aqui (no solo en PediatricHistoryTab.tsx) porque el mismo patron aplicara a
 * cualquier historia futura con campos Si/No/Sin-responder. */
export function TriStateRadioGroup({
  label,
  name,
  value,
  onChange,
}: {
  label: string
  name: string
  value: boolean | null
  onChange: (value: boolean | null) => void
}) {
  return (
    <div>
      <p className={styles.fieldsetLabel}>{label}</p>
      <div className={styles.checkboxGrid}>
        <label className={styles.checkboxItem}>
          <input
            type="radio"
            name={name}
            checked={value === null}
            onChange={() => onChange(null)}
          />
          Sin responder
        </label>
        <label className={styles.checkboxItem}>
          <input type="radio" name={name} checked={value === true} onChange={() => onChange(true)} />
          Sí
        </label>
        <label className={styles.checkboxItem}>
          <input
            type="radio"
            name={name}
            checked={value === false}
            onChange={() => onChange(false)}
          />
          No
        </label>
      </div>
    </div>
  )
}

/** Indicador visible arriba del formulario mientras se esta "editando" una
 * entrada ya existente (en vez de agregar una nueva) -- parte del patron
 * "editar" generico de la ronda 2.2 (ver historyHelpers.ts para
 * `latestActive`/`saveWithAutoCorrection`, que no son componentes y por eso
 * viven en ese otro modulo -- mismo criterio que `triStateRow`). */
export function EditingBanner({ createdAt }: { createdAt: string }) {
  return (
    <p className={styles.editingBanner}>
      Editando el registro capturado el {new Date(createdAt).toLocaleString('es-MX')}. Al guardar,
      se reemplazará por la versión corregida (el registro anterior queda anulado para
      auditoría, nunca se borra).
    </p>
  )
}
