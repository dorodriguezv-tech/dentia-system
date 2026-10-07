import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import * as api from './api'
import styles from './GlobalSearch.module.css'
import { useGlobalSearchStore } from './searchStore'
import { STATUS_LABELS, type PatientListItemOut } from './types'

const DEBOUNCE_MS = 250
const MIN_QUERY_LENGTH = 2

/** Mantiene el atajo Ctrl+K activo en toda la app autenticada; el panel solo se monta
 * mientras esta abierto, para que su estado (query, resultados) siempre arranque limpio. */
export function GlobalSearch() {
  const open = useGlobalSearchStore((s) => s.open)
  const setOpen = useGlobalSearchStore((s) => s.setOpen)
  const toggle = useGlobalSearchStore((s) => s.toggle)

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        toggle()
      } else if (event.key === 'Escape') {
        setOpen(false)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [toggle, setOpen])

  if (!open) return null
  return <SearchPanel onClose={() => setOpen(false)} />
}

function SearchPanel({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<PatientListItemOut[]>([])

  useEffect(() => {
    const trimmed = query.trim()
    // A2: con menos de 2 caracteres la busqueda por palabra (tolerante a errores)
    // es puro ruido -- casi cualquier nombre tiene una palabra que empieza o se
    // parece a una sola letra. No hace falta limpiar `results` aqui: `visibleResults`
    // ya lo ignora mientras el texto sea mas corto que el minimo.
    if (trimmed.length < MIN_QUERY_LENGTH) return

    const controller = new AbortController()
    const timeout = setTimeout(() => {
      api
        .searchPatients(trimmed, controller.signal)
        .then(setResults)
        .catch(() => undefined)
    }, DEBOUNCE_MS)
    return () => {
      clearTimeout(timeout)
      controller.abort()
    }
  }, [query])

  function handleSelect(patientId: string) {
    onClose()
    navigate(`/pacientes/${patientId}`)
  }

  const trimmedQuery = query.trim()
  const visibleResults = trimmedQuery.length >= MIN_QUERY_LENGTH ? results : []

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.panel} onClick={(e) => e.stopPropagation()}>
        <input
          className={styles.input}
          type="text"
          autoFocus
          placeholder="Buscar paciente por nombre, telefono, correo o expediente..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {trimmedQuery.length > 0 && trimmedQuery.length < MIN_QUERY_LENGTH && (
          <ul className={styles.results}>
            <li className={styles.empty}>Escribe al menos 2 caracteres.</li>
          </ul>
        )}
        {trimmedQuery.length >= MIN_QUERY_LENGTH && (
          <ul className={styles.results}>
            {visibleResults.map((patient) => (
              <li key={patient.id} className={styles.resultItem}>
                <button type="button" onClick={() => handleSelect(patient.id)}>
                  <span>{patient.full_name}</span>
                  <span className={styles.resultMeta}>
                    #{patient.expediente_number} · {STATUS_LABELS[patient.status]}
                  </span>
                </button>
              </li>
            ))}
            {visibleResults.length === 0 && <li className={styles.empty}>Sin resultados.</li>}
          </ul>
        )}
        <div className={styles.hint}>Ctrl+K para abrir o cerrar · Esc para cerrar</div>
      </div>
    </div>
  )
}
