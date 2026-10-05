export function toDateKey(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function startOfDay(d: Date): Date {
  const r = new Date(d)
  r.setHours(0, 0, 0, 0)
  return r
}

export function addDays(d: Date, n: number): Date {
  const r = new Date(d)
  r.setDate(r.getDate() + n)
  return r
}

/** Lunes de la semana que contiene `d`. */
export function startOfWeek(d: Date): Date {
  const r = startOfDay(d)
  const day = (r.getDay() + 6) % 7 // 0 = lunes
  return addDays(r, -day)
}

export function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1)
}

/** 42 dias (6 semanas) empezando en lunes, cubriendo el mes completo con relleno. */
export function monthGridDays(d: Date): Date[] {
  const gridStart = startOfWeek(startOfMonth(d))
  return Array.from({ length: 42 }, (_, i) => addDays(gridStart, i))
}

export function combineDateAndTime(date: Date, hour: number, minute: number): Date {
  const r = startOfDay(date)
  r.setHours(hour, minute, 0, 0)
  return r
}

export function formatTime(d: Date): string {
  return d.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })
}
