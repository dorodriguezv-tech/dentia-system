import { STATUS_COLORS } from './catalog'
import styles from './CalendarGrid.module.css'
import { formatTime, toDateKey } from './dateUtils'
import type { AppointmentListItemOut } from './types'

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

interface CalendarGridProps {
  dates: Date[]
  appointments: AppointmentListItemOut[]
  onSlotClick: (date: Date, hour: number, minute: number) => void
  onDropAppointment: (appointmentId: string, date: Date, hour: number, minute: number) => void
  onAppointmentClick: (appointment: AppointmentListItemOut) => void
}

export function CalendarGrid({
  dates,
  appointments,
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

  return (
    <div
      className={styles.grid}
      style={{ gridTemplateColumns: `56px repeat(${dates.length}, 1fr)` }}
    >
      <div className={styles.corner} />
      {dates.map((date) => (
        <div key={toDateKey(date)} className={styles.dayHeader}>
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
              const label = `Agendar cita: ${date.toLocaleDateString('es-MX', {
                weekday: 'long',
                day: 'numeric',
                month: 'long',
              })}, ${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`
              return (
                <div
                  key={i}
                  role="button"
                  tabIndex={0}
                  aria-label={label}
                  className={styles.slot}
                  style={{ height: SLOT_PX }}
                  onClick={() => onSlotClick(date, hour, minute)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      onSlotClick(date, hour, minute)
                    }
                  }}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault()
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
