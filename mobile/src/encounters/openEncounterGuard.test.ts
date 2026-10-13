import { Alert } from 'react-native';

import { guardSingleOpenEncounter } from './openEncounterGuard';

jest.mock('expo-router', () => ({ router: { push: jest.fn() } }));

describe('guardSingleOpenEncounter (M4)', () => {
  it('sin consulta abierta, inicia la nueva directamente sin preguntar', () => {
    const startNew = jest.fn();
    const alertSpy = jest.spyOn(Alert, 'alert');

    guardSingleOpenEncounter(null, startNew);

    expect(startNew).toHaveBeenCalledTimes(1);
    expect(alertSpy).not.toHaveBeenCalled();
  });

  it('con una consulta abierta, pregunta antes de iniciar otra', () => {
    const startNew = jest.fn();
    const alertSpy = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);

    guardSingleOpenEncounter(
      { id: 'enc-1', patient_id: 'pat-1', patient_full_name: 'Laura Sánchez', started_at: new Date().toISOString() },
      startNew,
    );

    expect(startNew).not.toHaveBeenCalled();
    expect(alertSpy).toHaveBeenCalledTimes(1);
    expect(alertSpy.mock.calls[0]?.[1]).toContain('Laura Sánchez');
  });

  it('"Dejarla en borrador" sí llama a startNew', () => {
    const startNew = jest.fn();
    jest.spyOn(Alert, 'alert').mockImplementation((_title, _msg, buttons) => {
      buttons?.find((b) => b.text === 'Dejarla en borrador')?.onPress?.();
    });

    guardSingleOpenEncounter(
      { id: 'enc-1', patient_id: 'pat-1', patient_full_name: 'Laura Sánchez', started_at: new Date().toISOString() },
      startNew,
    );

    expect(startNew).toHaveBeenCalledTimes(1);
  });
});
