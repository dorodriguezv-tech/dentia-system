import { STATUS_COLORS } from './catalog'
import styles from './CalendarGrid.module.css'
import { combineDateAndTime, formatTime, startOfDay, toDateKey } from './dateUtils'
import type { AppointmentListItemOut, WorkingHoursOut } from './types'

const DAY_START_HOUR = 7
const DAY_END_HOUR = 21
const SLOT_MINUTES = 30
const SLOT_PX = 32
const SLOTS_PER_HOUR = 60 / SLOT_MINUTES
const TOTAL_SLOTS = (DAY_END_HOUR - DAY_START_HOUR) * SLOTS_PER_HOUR
const HOURS = Array.from({ length: DAY_END_HOUR - DAY_START_HOUR }, (_, i) => DAY_START_HOUR + i)

function minutesFromGridStart(d: Date): number {
  return (d.getHours() - DAY_START_HOUR) * 60 + d.getMinutes()
}

// Date.getDay() da 0=domingo..6=sabado; el backend usa 0=lunes..6=domingo
// (ProviderWorkingHours.weekday, docs/02_ARQUITECTURA.md).
function toBackendWeekday(jsWeekday: number): number {
  return (jsWeekday + 6) % 7
}

/** Minutos no laborales (comida, fuera de horario, domingo) se muestran
 * sombrados pero siguen siendo clicables -- el odontologo puede agendar una
 * urgencia fuera de horario a propósito; lo que no existe es un horario
 * laboral que la app invente por su cuenta. */
function isWorkingMinute(workingHours: WorkingHoursOut[], date: Date, minuteOfDay: number): boolean {
  const weekday = toBackendWeekday(date.getDay())
  return workingHours.some((wh) => {
    if (wh.weekday !== weekday) return false
    const [startH, startM] = wh.start_time.split(':').map(Number)
    const [endH, endM] = wh.end_time.split(':').map(Number)
    const startMin = startH * 60 + startM
    const endMin = endH * 60 + endM
    return minuteOfDay >= startMin && minuteOfDay < endMin
  })
}

interface CalendarGridProps {
  dates: Date[]
  appointments: AppointmentListItemOut[]
  workingHours: WorkingHoursOut[]
  onSlotClick: (date: Date, hour: number, minute: number) => void
  onDropAppointment: (appointmentId: string, date: Date, hour: number, minute: number) => void
  onAppointmentClick: (appointment: AppointmentListItemOut) => void
}

export function CalendarGrid({
  dates,
  appointments,
  workingHours,
  onSlotClick,
  onDropAppointment,
  onAppointmentClick,
}: CalendarGridProps) {
  const byDate = new Map<string, AppointmentListItemOut[]>()
  for (const appointment of appointments) {
    const key = toDateKey(new Date(appointment.starts_at))
    const list = byDate.get(key) ?? []
    list.push(appointment)
    byDate.set(key, list)
  }

  // No se pueden agendar citas en un horario que ya paso (el backend lo rechaza con
  // PAST_TIME_SLOT, ver agenda/service.py::_assert_not_past); aqui solo se sombrea y
  // se evita que parezca una opcion valida -- a diferencia de "fuera de horario
  // laboral" (isOffHours), que sigue siendo clicable a proposito para urgencias.
  const now = new Date()
  const today = startOfDay(now)

  return (
    <div
      className={styles.grid}
      style={{ gridTemplateColumns: `56px repeat(${dates.length}, 1fr)` }}
    >
      <div className={styles.corner} />
      {dates.map((date) => (
        <div
          key={toDateKey(date)}
          className={startOfDay(date) < today ? `${styles.dayHeader} ${styles.dayHeaderPast}` : styles.dayHeader}
        >
          {date.toLocaleDateString('es-MX', { weekday: 'short', day: 'numeric', month: 'short' })}
        </div>
      ))}

      <div className={styles.timeAxis}>
        {HOURS.map((hour) => (
          <div key={hour} className={styles.hourLabel} style={{ height: SLOT_PX * SLOTS_PER_HOUR }}>
            {String(hour).padStart(2, '0')}:00
          </div>
        ))}
      </div>

      {dates.map((date) => {
        const dayAppointments = byDate.get(toDateKey(date)) ?? []
        return (
          <div
            key={toDateKey(date)}
            className={styles.dayColumn}
            style={{ height: TOTAL_SLOTS * SLOT_PX }}
          >
            {Array.from({ length: TOTAL_SLOTS }, (_, i) => {
              const totalMin = i * SLOT_MINUTES
              const hour = DAY_START_HOUR + Math.floor(totalMin / 60)
              const minute = totalMin % 60
              // Sin horario cargado (p. ej. agrupando por gabinete, sin un solo
              // profesional) no se sombrea nada -- "no se sabe" no es "cerrado".
              const isOffHours =
                workingHours.length > 0 && !isWorkingMinute(workingHours, date, hour * 60 + minute)
              const isPast = combineDateAndTime(date, hour, minute) < now
              const label = `Agendar cita${isPast ? ' (horario ya paso)' : isOffHours ? ' (fuera de horario laboral, solo urgencias)' : ''}: ${date.toLocaleDateString(
                'es-MX',
                { weekday: 'long', day: 'numeric', month: 'long' },
              )}, ${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`
              let className = styles.slot
              if (isPast) className = `${styles.slot} ${styles.slotPast}`
              else if (isOffHours) className = `${styles.slot} ${styles.slotOffHours}`
              return (
                <div
                  key={i}
                  role="button"
                  tabIndex={isPast ? -1 : 0}
                  aria-disabled={isPast}
                  aria-label={label}
                  className={className}
                  style={{ height: SLOT_PX }}
                  onClick={() => {
                    if (!isPast) onSlotClick(date, hour, minute)
                  }}
                  onKeyDown={(e) => {
                    if (!isPast && (e.key === 'Enter' || e.key === ' ')) {
                      e.preventDefault()
                      onSlotClick(date, hour, minute)
                    }
                  }}
                  onDragOver={(e) => {
                    if (!isPast) e.preventDefault()
                  }}
                  onDrop={(e) => {
                    e.preventDefault()
                    if (isPast) return
                    const id = e.dataTransfer.getData('text/plain')
                    if (id) onDropAppointment(id, date, hour, minute)
                  }}
                />
              )
            })}

            <div className={styles.overlay}>
              {dayAppointments.map((appointment) => {
                const start = new Date(appointment.starts_at)
                const end = new Date(appointment.ends_at)
                const top = (minutesFromGridStart(start) / SLOT_MINUTES) * SLOT_PX
                const height = Math.max(
                  SLOT_PX / 2,
                  ((end.getTime() - start.getTime()) / 60000 / SLOT_MINUTES) * SLOT_PX,
                )
                return (
                  <div
                    key={appointment.id}
                    role="button"
                    tabIndex={0}
                    aria-label={`Cita de ${appointment.patient_full_name} a las ${formatTime(start)}, estado ${appointment.status}`}
                    className={styles.appointment}
                    draggable={
                      appointment.status === 'RESERVADA' || appointment.status === 'CONFIRMADA'
                    }
                    onDragStart={(e) => e.dataTransfer.setData('text/plain', appointment.id)}
                    onClick={() => onAppointmentClick(appointment)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        onAppointmentClick(appointment)
                      }
                    }}
                    style={{
                      top,
                      height,
                      borderLeftColor: appointment.provider_color,
                      backgroundColor: STATUS_COLORS[appointment.status],
                    }}
                  >
                    <strong>{formatTime(start)}</strong> {appointment.patient_full_name}
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}
