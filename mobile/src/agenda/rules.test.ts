import { canTransition, isEditable, reasonRequired } from './rules';
import type { AppointmentStatus } from '@/api/types';

/** Mismas transiciones que backend/app/modules/agenda/rules.py — si el backend
 * cambia la máquina de estados, esta prueba debe actualizarse a la vez. */
describe('canTransition', () => {
  const cases: [AppointmentStatus, AppointmentStatus, boolean][] = [
    ['RESERVADA', 'CONFIRMADA', true],
    ['RESERVADA', 'EN_SALA', true],
    ['RESERVADA', 'EN_ATENCION', true],
    ['RESERVADA', 'CANCELADA', true],
    ['RESERVADA', 'NO_SHOW', true],
    ['RESERVADA', 'REPROGRAMADA', true],
    ['RESERVADA', 'TERMINADA', false],
    ['CONFIRMADA', 'EN_SALA', true],
    ['CONFIRMADA', 'RESERVADA', false],
    ['EN_SALA', 'EN_ATENCION', true],
    ['EN_SALA', 'REPROGRAMADA', false],
    ['EN_ATENCION', 'TERMINADA', true],
    ['EN_ATENCION', 'CANCELADA', false],
    ['TERMINADA', 'RESERVADA', false],
    ['CANCELADA', 'RESERVADA', false],
    ['NO_SHOW', 'RESERVADA', false],
    ['REPROGRAMADA', 'RESERVADA', false],
  ];

  it.each(cases)('%s -> %s es %s', (current, target, expected) => {
    expect(canTransition(current, target)).toBe(expected);
  });
});

describe('isEditable', () => {
  it('solo RESERVADA y CONFIRMADA se pueden reprogramar', () => {
    expect(isEditable('RESERVADA')).toBe(true);
    expect(isEditable('CONFIRMADA')).toBe(true);
    expect(isEditable('EN_SALA')).toBe(false);
    expect(isEditable('TERMINADA')).toBe(false);
  });
});

describe('reasonRequired', () => {
  it('CANCELADA y NO_SHOW exigen motivo, el resto no', () => {
    expect(reasonRequired('CANCELADA')).toBe(true);
    expect(reasonRequired('NO_SHOW')).toBe(true);
    expect(reasonRequired('CONFIRMADA')).toBe(false);
    expect(reasonRequired('EN_SALA')).toBe(false);
  });
});
