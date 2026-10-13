import { resolveDark } from './theme';

describe('resolveDark (M2: preferencia de tema)', () => {
  it('"system" sigue el tema del teléfono', () => {
    expect(resolveDark('system', true)).toBe(true);
    expect(resolveDark('system', false)).toBe(false);
  });

  it('"light" fuerza claro sin importar el teléfono', () => {
    expect(resolveDark('light', true)).toBe(false);
    expect(resolveDark('light', false)).toBe(false);
  });

  it('"dark" fuerza oscuro sin importar el teléfono', () => {
    expect(resolveDark('dark', true)).toBe(true);
    expect(resolveDark('dark', false)).toBe(true);
  });
});
