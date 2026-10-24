import { useEffect, useState } from 'react'
import * as api from './api'
import styles from './WorkingHoursPage.module.css'
import type { ProviderOut, WorkingHoursOut } from './types'

const WEEKDAYS = [
  { value: 0, label: 'Lunes' },
  { value: 1, label: 'Martes' },
  { value: 2, label: 'Miercoles' },
  { value: 3, label: 'Jueves' },
  { value: 4, label: 'Viernes' },
  { value: 5, label: 'Sabado' },
  { value: 6, label: 'Domingo' },
]

export function WorkingHoursPage() {
  const [providers, setProviders] = useState<ProviderOut[]>([])
  const [providerId, setProviderId] = useState<string>('')
  const [hours, setHours] = useState<WorkingHoursOut[]>([])
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [newWeekday, setNewWeekday] = useState(0)
  const [newStart, setNewStart] = useState('08:00')
  const [newEnd, setNewEnd] = useState('18:00')

  useEffect(() => {
    api.listProviders().then((list) => {
      setProviders(list)
      if (list.length > 0) setProviderId(list[0].id)
    })
  }, [])

  useEffect(() => {
    if (!providerId) return
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const list = await api.listWorkingHours(providerId)
        if (!cancelled) setHours(list)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [providerId])

  async function refresh() {
    const list = await api.listWorkingHours(providerId)
    setHours(list)
  }

  async function handleAddBlock() {
    if (!providerId) return
    setBusy(true)
    setMessage(null)
    try {
      await api.createWorkingHours(providerId, {
        weekday: newWeekday,
        start_time: newStart,
        end_time: newEnd,
      })
      await refresh()
      setMessage('Bloque agregado.')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'No se pudo agregar el bloque.')
    } finally {
      setBusy(false)
    }
  }

  async function handleDeleteBlock(itemId: string) {
    if (!providerId) return
    setBusy(true)
    setMessage(null)
    try {
      await api.deleteWorkingHours(providerId, itemId)
      await refresh()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'No se pudo eliminar el bloque.')
    } finally {
      setBusy(false)
    }
  }

  async function handleOpenAllWeek() {
    if (!providerId) return
    if (
      !window.confirm(
        'Esto borra los bloques de horario actuales de este profesional y los reemplaza por ' +
          'un horario abierto las 24 horas, los 7 dias de la semana (sin restriccion). ¿Continuar?',
      )
    ) {
      return
    }
    setBusy(true)
    setMessage(null)
    try {
      for (const block of hours) {
        await api.deleteWorkingHours(providerId, block.id)
      }
      for (const day of WEEKDAYS) {
        await api.createWorkingHours(providerId, {
          weekday: day.value,
          start_time: '00:00',
          end_time: '23:59',
        })
      }
      await refresh()
      setMessage('Horario abierto toda la semana, sin restriccion.')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'No se pudo abrir el horario completo.')
    } finally {
      setBusy(false)
    }
  }

  const hoursByDay = WEEKDAYS.map((day) => ({
    ...day,
    blocks: hours
      .filter((h) => h.weekday === day.value)
      .sort((a, b) => a.start_time.localeCompare(b.start_time)),
  }))

  return (
    <section>
      <h1>Horarios</h1>
      <p className={styles.hint}>
        Define en que dias y horas aparece cada profesional como disponible en la agenda. Las
        horas fuera de estos bloques se muestran sombreadas en el calendario, pero{' '}
        <strong>no bloquean</strong> agendar una cita igual — es solo informativo.
      </p>

      <div className={styles.field}>
        <label htmlFor="provider">Profesional</label>
        <select id="provider" value={providerId} onChange={(e) => setProviderId(e.target.value)}>
          {providers.map((p) => (
            <option key={p.id} value={p.id}>
              {p.full_name}
            </option>
          ))}
        </select>
      </div>

      {message && <div className={styles.message}>{message}</div>}

      <button
        type="button"
        className={styles.openWeekButton}
        onClick={handleOpenAllWeek}
        disabled={busy || !providerId}
      >
        Horario abierto toda la semana (sin restriccion)
      </button>

      {loading ? (
        <p>Cargando horario...</p>
      ) : (
        <div className={styles.dayGrid}>
          {hoursByDay.map((day) => (
            <div key={day.value} className={styles.dayCard}>
              <h3>{day.label}</h3>
              {day.blocks.length === 0 ? (
                <p className={styles.closed}>Sin horario definido</p>
              ) : (
                <ul className={styles.blockList}>
                  {day.blocks.map((block) => (
                    <li key={block.id}>
                      {block.start_time.slice(0, 5)} - {block.end_time.slice(0, 5)}
                      <button
                        type="button"
                        className={styles.deleteButton}
                        onClick={() => handleDeleteBlock(block.id)}
                        disabled={busy}
                        aria-label={`Eliminar bloque ${block.start_time}-${block.end_time} de ${day.label}`}
                      >
                        Eliminar
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}

      <div className={styles.addForm}>
        <h2>Agregar un bloque manual</h2>
        <div className={styles.addFormRow}>
          <label>
            Dia
            <select value={newWeekday} onChange={(e) => setNewWeekday(Number(e.target.value))}>
              {WEEKDAYS.map((d) => (
                <option key={d.value} value={d.value}>
                  {d.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Desde
            <input type="time" value={newStart} onChange={(e) => setNewStart(e.target.value)} />
          </label>
          <label>
            Hasta
            <input type="time" value={newEnd} onChange={(e) => setNewEnd(e.target.value)} />
          </label>
          <button
            type="button"
            className={styles.primaryButton}
            onClick={handleAddBlock}
            disabled={busy || !providerId}
          >
            Agregar bloque
          </button>
        </div>
      </div>
    </section>
  )
}
