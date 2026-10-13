import { applicableSurfaces, surfaceForZone } from './Odontogram';

describe('surfaceForZone / applicableSurfaces (M5: selección múltiple de superficies)', () => {
  it('pieza posterior (molar) usa oclusal en el centro', () => {
    expect(surfaceForZone(16, 'center')).toBe('O');
  });

  it('pieza anterior (incisivo) usa incisal en el centro', () => {
    expect(surfaceForZone(11, 'center')).toBe('I');
  });

  it('cuadrantes superiores (1,2) usan palatina abajo; inferiores (3,4) usan lingual', () => {
    expect(surfaceForZone(16, 'bottom')).toBe('P');
    expect(surfaceForZone(26, 'bottom')).toBe('P');
    expect(surfaceForZone(36, 'bottom')).toBe('L');
    expect(surfaceForZone(46, 'bottom')).toBe('L');
  });

  it('arriba siempre es vestibular', () => {
    expect(surfaceForZone(11, 'top')).toBe('V');
    expect(surfaceForZone(46, 'top')).toBe('V');
  });

  it('mesial/distal se invierten según el lado del paciente (línea media)', () => {
    // Cuadrante 1 (superior derecho del paciente): mesial hacia la línea media = derecha
    expect(surfaceForZone(11, 'left')).toBe('D');
    expect(surfaceForZone(11, 'right')).toBe('M');
    // Cuadrante 2 (superior izquierdo del paciente): se invierte
    expect(surfaceForZone(21, 'left')).toBe('M');
    expect(surfaceForZone(21, 'right')).toBe('D');
  });

  it('applicableSurfaces devuelve las 5 superficies reales de la pieza, sin repetir', () => {
    const surfaces = applicableSurfaces(36);
    expect(surfaces).toHaveLength(5);
    expect(new Set(surfaces).size).toBe(5);
    expect(surfaces).toEqual(expect.arrayContaining(['V', 'L', 'O', 'M', 'D']));
  });

  it('en una pieza anterior, la superficie central es incisal, no oclusal', () => {
    expect(applicableSurfaces(11)).toEqual(expect.arrayContaining(['I']));
    expect(applicableSurfaces(11)).not.toEqual(expect.arrayContaining(['O']));
  });
});
