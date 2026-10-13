/** Rango [inicio, fin) de un día local, en ISO con zona horaria, desplazado `offset` días. */
export function dayRange(offset = 0, now = new Date()): { from: string; to: string; label: string } {
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset, 0, 0, 0, 0);
  const end = new Date(start.getFullYear(), start.getMonth(), start.getDate() + 1, 0, 0, 0, 0);
  return { from: toLocalIso(start), to: toLocalIso(end), label: dayLabel(offset, start) };
}

function pad(n: number) {
  return String(n).padStart(2, '0');
}

/** 2026-10-11T00:00:00-06:00 (FastAPI lo interpreta con su zona, sin perder el día local). */
export function toLocalIso(d: Date): string {
  const tz = -d.getTimezoneOffset();
  const sign = tz >= 0 ? '+' : '-';
  const abs = Math.abs(tz);
  return (
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:00` +
    `${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`
  );
}

export function dayLabel(offset: number, date: Date): string {
  if (offset === 0) return 'Hoy';
  if (offset === 1) return 'Mañana';
  if (offset === -1) return 'Ayer';
  return date.toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long' });
}

export function hhmm(iso: string): string {
  const d = new Date(iso);
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** "2026-11-02": lo que espera `day` en GET /appointments/availability. */
export function dateKey(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function addDays(d: Date, days: number): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + days);
}

/** M3: combina un día (sin hora) con una hora escrita a mano "H:MM"/"HH:MM".
 * null si el texto no tiene ese formato o la hora/minuto están fuera de rango. */
export function combineDayAndTime(day: Date, time: string): Date | null {
  const m = /^(\d{1,2}):(\d{2})$/.exec(time.trim());
  if (!m || !m[1] || !m[2]) return null;
  const hh = Number(m[1]);
  const mm = Number(m[2]);
  if (hh > 23 || mm > 59) return null;
  return new Date(day.getFullYear(), day.getMonth(), day.getDate(), hh, mm, 0, 0);
}
