import { STATUS_COLORS } from './catalog'
import styles from './MonthGrid.module.css'
import { toDateKey } from './dateUtils'
import type { AppointmentListItemOut } from './types'

const WEEKDAY_LABELS = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom']

interface MonthGridProps {
  days: Date[]
  month: Date
  appointments: AppointmentListItemOut[]
  onDayClick: (date: Date) => void
}

export function MonthGrid({ days, month, appointments, onDayClick }: MonthGridProps) {
  const byDate = new Map<string, AppointmentListItemOut[]>()
  for (const appointment of appointments) {
    const key = toDateKey(new Date(appointment.starts_at))
    const list = byDate.get(key) ?? []
    list.push(appointment)
    byDate.set(key, list)
  }

  return (
    <div className={styles.grid}>
      {WEEKDAY_LABELS.map((label) => (
        <div key={label} className={styles.weekdayHeader}>
          {label}
        </div>
      ))}
      {days.map((day) => {
        const key = toDateKey(day)
        const dayAppointments = byDate.get(key) ?? []
        const inMonth = day.getMonth() === month.getMonth()
        return (
          <button
            key={key}
            type="button"
            className={inMonth ? styles.day : styles.dayOutside}
            onClick={() => onDayClick(day)}
          >
            <span className={styles.dayNumber}>{day.getDate()}</span>
            <span className={styles.dots}>
              {dayAppointments.slice(0, 4).map((appointment) => (
                <span
                  key={appointment.id}
                  className={styles.dot}
                  style={{ backgroundColor: STATUS_COLORS[appointment.status] }}
                />
              ))}
              {dayAppointments.length > 4 && <span className={styles.more}>+{dayAppointments.length - 4}</span>}
            </span>
          </button>
        )
      })}
    </div>
  )
}
