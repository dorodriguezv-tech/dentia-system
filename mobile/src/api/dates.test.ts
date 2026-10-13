import { combineDayAndTime, dateKey } from './dates';

describe('dateKey', () => {
  it('formatea como YYYY-MM-DD con ceros a la izquierda', () => {
    expect(dateKey(new Date(2026, 0, 5))).toBe('2026-01-05');
    expect(dateKey(new Date(2026, 10, 2))).toBe('2026-11-02');
  });
});

describe('combineDayAndTime (M3: hora manual en Nueva cita/Reprogramar)', () => {
  const day = new Date(2026, 10, 2); // 2 de noviembre de 2026

  it('combina un día con una hora válida', () => {
    const result = combineDayAndTime(day, '14:30');
    expect(result).not.toBeNull();
    expect(result?.getFullYear()).toBe(2026);
    expect(result?.getMonth()).toBe(10);
    expect(result?.getDate()).toBe(2);
    expect(result?.getHours()).toBe(14);
    expect(result?.getMinutes()).toBe(30);
  });

  it('acepta una hora de un solo dígito', () => {
    expect(combineDayAndTime(day, '9:05')?.getHours()).toBe(9);
  });

  it('rechaza texto sin el formato H:MM', () => {
    expect(combineDayAndTime(day, '')).toBeNull();
    expect(combineDayAndTime(day, '2pm')).toBeNull();
    expect(combineDayAndTime(day, '14')).toBeNull();
    expect(combineDayAndTime(day, '14:3')).toBeNull();
  });

  it('rechaza horas o minutos fuera de rango', () => {
    expect(combineDayAndTime(day, '24:00')).toBeNull();
    expect(combineDayAndTime(day, '10:60')).toBeNull();
  });
});
