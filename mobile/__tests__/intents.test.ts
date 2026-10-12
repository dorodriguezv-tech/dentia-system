import { needsImplicitConfirm, normalize, parseIntent, stripWakeWord } from '../src/voice/intents';

describe('normalize / stripWakeWord', () => {
  it('quita acentos y signos', () => {
    expect(normalize('¿Mañana, Dentía?')).toBe('manana dentia');
  });
  it('quita la palabra de activación', () => {
    expect(stripWakeWord('oye dentia abre la agenda')).toBe('abre la agenda');
    expect(stripWakeWord('dencia agenda de hoy')).toBe('agenda de hoy');
  });
});

describe('parseIntent', () => {
  const cases: [string, unknown][] = [
    ['Dentia, abre el expediente de Ana López', { type: 'OPEN_PATIENT', name: 'ana lopez' }],
    ['abre la ficha del paciente José Martínez Ruiz', { type: 'OPEN_PATIENT', name: 'jose martinez ruiz' }],
    ['busca a María de la Luz Pérez', { type: 'OPEN_PATIENT', name: 'maria de la luz perez' }],
    ['muestra el odontograma de Pedro Gómez por favor', { type: 'OPEN_PATIENT', name: 'pedro gomez' }],
    ['agenda de hoy', { type: 'SHOW_AGENDA', dayOffset: 0 }],
    ['¿qué citas tengo hoy?', { type: 'SHOW_AGENDA', dayOffset: 0 }],
    ['Dentia, muéstrame las citas de mañana', { type: 'SHOW_AGENDA', dayOffset: 1 }],
    ['agenda de pasado mañana', { type: 'SHOW_AGENDA', dayOffset: 2 }],
    ['¿quién sigue?', { type: 'NEXT_APPOINTMENT' }],
    ['siguiente paciente', { type: 'NEXT_APPOINTMENT' }],
    ['Laura Sánchez ya llegó', { type: 'CHECK_IN', name: 'laura sanchez' }],
    ['pasa a sala a Roberto Díaz', { type: 'CHECK_IN', name: 'roberto diaz' }],
    ['empieza el dictado', { type: 'START_DICTATION' }],
    ['No, cancela', { type: 'CANCEL' }],
    ['sí', { type: 'CONFIRM' }],
    ['ayuda', { type: 'HELP' }],
    ['Dentia', { type: 'HELP' }],
  ];
  it.each(cases)('%s', (input, expected) => {
    expect(parseIntent(input)).toEqual(expected);
  });

  it('lo que no reconoce cae en UNKNOWN, nunca se inventa una acción', () => {
    expect(parseIntent('receta amoxicilina de 500').type).toBe('UNKNOWN');
    expect(parseIntent('borra al paciente').type).toBe('UNKNOWN');
  });

  it('solo las órdenes con efecto usan confirmación implícita', () => {
    expect(needsImplicitConfirm({ type: 'OPEN_PATIENT', name: 'x' })).toBe(true);
    expect(needsImplicitConfirm({ type: 'SHOW_AGENDA', dayOffset: 0 })).toBe(false);
  });
});
