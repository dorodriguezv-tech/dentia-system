import { performLogout, type LogoutDeps } from './logout';

function makeDeps(overrides: Partial<LogoutDeps> = {}): { deps: LogoutDeps; calls: string[] } {
  const calls: string[] = [];
  const deps: LogoutDeps = {
    refreshToken: 'rt-1',
    logoutApi: async () => {
      calls.push('logoutApi');
    },
    stopVoice: () => calls.push('stopVoice'),
    clearQueryCache: () => calls.push('clearQueryCache'),
    clearSession: async () => {
      calls.push('clearSession');
    },
    navigateToLogin: () => calls.push('navigateToLogin'),
    ...overrides,
  };
  return { deps, calls };
}

describe('performLogout', () => {
  it('con red: llama /auth/logout, limpia todo y navega a Login', async () => {
    const { deps, calls } = makeDeps();
    await performLogout(deps);
    expect(calls).toEqual(['logoutApi', 'stopVoice', 'clearQueryCache', 'clearSession', 'navigateToLogin']);
  });

  it('sin red: el error de logoutApi no impide limpiar y navegar a Login', async () => {
    const { deps, calls } = makeDeps({
      logoutApi: async () => {
        calls.push('logoutApi');
        throw new Error('No se pudo conectar con el servidor de la clínica.');
      },
    });
    await performLogout(deps);
    expect(calls).toEqual(['logoutApi', 'stopVoice', 'clearQueryCache', 'clearSession', 'navigateToLogin']);
  });

  it('con token vencido (401): igual termina en Login', async () => {
    const { deps, calls } = makeDeps({
      logoutApi: async () => {
        calls.push('logoutApi');
        throw new Error('401');
      },
    });
    await performLogout(deps);
    expect(calls[calls.length - 1]).toBe('navigateToLogin');
    expect(calls).toContain('clearSession');
  });

  it('sin refreshToken: no llama a logoutApi pero igual limpia y navega', async () => {
    const { deps, calls } = makeDeps({ refreshToken: null });
    await performLogout(deps);
    expect(calls).toEqual(['stopVoice', 'clearQueryCache', 'clearSession', 'navigateToLogin']);
  });

  it('si stopVoice falla, de todos modos se limpia la sesión y se navega a Login', async () => {
    const { deps, calls } = makeDeps({
      stopVoice: () => {
        calls.push('stopVoice');
        throw new Error('no debería propagarse');
      },
    });
    await performLogout(deps);
    expect(calls).toEqual(['logoutApi', 'stopVoice', 'clearQueryCache', 'clearSession', 'navigateToLogin']);
  });

  it('si clearSession falla, navigateToLogin se llama de todos modos', async () => {
    const { deps, calls } = makeDeps({
      clearSession: async () => {
        calls.push('clearSession');
        throw new Error('SecureStore no disponible');
      },
    });
    await performLogout(deps);
    expect(calls).toEqual(['logoutApi', 'stopVoice', 'clearQueryCache', 'clearSession', 'navigateToLogin']);
  });

  it('navigateToLogin siempre se llama al final, incluso si clearQueryCache falla', async () => {
    const { deps, calls } = makeDeps({
      clearQueryCache: () => {
        calls.push('clearQueryCache');
        throw new Error('inesperado');
      },
    });
    await performLogout(deps);
    expect(calls[calls.length - 1]).toBe('navigateToLogin');
  });
});
