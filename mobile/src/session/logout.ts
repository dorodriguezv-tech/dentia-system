/**
 * Lógica de "cerrar sesión" (M1, docs/06_APP_MOVIL_V1_1_PARIDAD.md), separada de la
 * pantalla para poder probarla sin React Native (mobile/CLAUDE.md §6).
 *
 * El cierre de sesión LOCAL (borrar tokens, caché, navegar a Login) debe completarse
 * siempre, sin importar si `/auth/logout` respondió, falló por red o por un token ya
 * vencido (401): por eso la limpieza vive en un `finally` y cada paso se protege por
 * separado, para que un error en uno no impida los siguientes.
 */

export interface LogoutDeps {
  /** Token guardado en SecureStore, o null si ya no hay sesión. */
  refreshToken: string | null;
  /** POST /auth/logout. Puede lanzar (red, 401, servidor caído). */
  logoutApi: (refreshToken: string) => Promise<void>;
  /** Detiene la voz de Dentia y cualquier grabación en curso en otra pantalla. */
  stopVoice: () => void;
  /** Borra la caché en memoria de TanStack Query. */
  clearQueryCache: () => void;
  /** Borra el access token (memoria), el refresh token (SecureStore) y el estado de sesión. */
  clearSession: () => Promise<void>;
  /** Reemplaza la navegación para que "Atrás" no regrese a una pantalla protegida. */
  navigateToLogin: () => void;
}

async function settle(fn: () => void | Promise<void>): Promise<void> {
  try {
    await fn();
  } catch {
    // La limpieza local nunca debe interrumpirse por un paso que falla.
  }
}

export async function performLogout(deps: LogoutDeps): Promise<void> {
  try {
    if (deps.refreshToken) {
      await deps.logoutApi(deps.refreshToken);
    }
  } catch {
    // Sin red, servidor caído o token ya vencido: el cierre local continúa igual.
  } finally {
    await settle(() => deps.stopVoice());
    await settle(() => deps.clearQueryCache());
    await settle(() => deps.clearSession());
    deps.navigateToLogin();
  }
}
