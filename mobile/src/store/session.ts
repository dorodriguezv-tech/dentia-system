import * as SecureStore from 'expo-secure-store';
import { create } from 'zustand';

import type { ClinicMembership, Me, UserPreferences } from '@/api/types';

/**
 * Sesión del usuario.
 *
 * Reglas de seguridad (docs/SEGURIDAD.md aplicado al móvil):
 *  - El access token (15 min) vive SOLO en memoria: nunca se escribe a disco.
 *  - El refresh token (8 h) se guarda en SecureStore (Android Keystore cifrado).
 *  - Ningún dato clínico se persiste en el teléfono: la caché de TanStack Query
 *    es solo en memoria y se borra al cerrar sesión o al bloquear la app.
 */

const K_SERVER = 'dentia.serverUrl';
const K_REFRESH = 'dentia.refreshToken';
const K_CLINIC = 'dentia.clinicId';

interface SessionState {
  hydrated: boolean;
  serverUrl: string | null;
  accessToken: string | null;
  refreshToken: string | null;
  clinicId: string | null;
  me: Me | null;
  clinics: ClinicMembership[];
  /** M2 (docs/06_APP_MOVIL_V1_1_PARIDAD.md): null hasta la primera carga de
   * GET /me/preferences; varias pantallas (tema, bloqueo, Dentia) la leen fuera
   * de un componente de React, por eso vive aquí y no solo en TanStack Query. */
  preferences: UserPreferences | null;
  /** La app se bloqueó por inactividad; requiere biometría o volver a entrar */
  locked: boolean;

  hydrate: () => Promise<void>;
  setServerUrl: (url: string) => Promise<void>;
  setTokens: (access: string, refresh: string) => Promise<void>;
  setAccessToken: (access: string) => void;
  setProfile: (me: Me, clinics: ClinicMembership[]) => void;
  setClinic: (clinicId: string) => Promise<void>;
  setPreferences: (preferences: UserPreferences) => void;
  setLocked: (locked: boolean) => void;
  clear: () => Promise<void>;
}

export const useSession = create<SessionState>((set) => ({
  hydrated: false,
  serverUrl: null,
  accessToken: null,
  refreshToken: null,
  clinicId: null,
  me: null,
  clinics: [],
  preferences: null,
  locked: false,

  hydrate: async () => {
    const [serverUrl, refreshToken, clinicId] = await Promise.all([
      SecureStore.getItemAsync(K_SERVER),
      SecureStore.getItemAsync(K_REFRESH),
      SecureStore.getItemAsync(K_CLINIC),
    ]);
    set({ serverUrl, refreshToken, clinicId, hydrated: true });
  },

  setServerUrl: async (url) => {
    const clean = normalizeServerUrl(url);
    await SecureStore.setItemAsync(K_SERVER, clean);
    set({ serverUrl: clean });
  },

  setTokens: async (access, refresh) => {
    await SecureStore.setItemAsync(K_REFRESH, refresh);
    set({ accessToken: access, refreshToken: refresh, locked: false });
  },

  setAccessToken: (access) => set({ accessToken: access }),

  setProfile: (me, clinics) => set({ me, clinics }),

  setClinic: async (clinicId) => {
    await SecureStore.setItemAsync(K_CLINIC, clinicId);
    set({ clinicId });
  },

  setPreferences: (preferences) => set({ preferences }),

  setLocked: (locked) => set({ locked }),

  clear: async () => {
    await Promise.all([
      SecureStore.deleteItemAsync(K_REFRESH),
      SecureStore.deleteItemAsync(K_CLINIC),
    ]);
    // serverUrl se conserva: es configuración del dispositivo, no de la sesión
    set({
      accessToken: null,
      refreshToken: null,
      clinicId: null,
      me: null,
      clinics: [],
      preferences: null,
      locked: false,
    });
  },
}));

/** Acepta "192.168.1.50:8001", "https://dentia.miclinica.mx" o con /api/v1 al final. */
export function normalizeServerUrl(raw: string): string {
  let url = raw.trim();
  if (!/^https?:\/\//i.test(url)) url = `https://${url}`;
  url = url.replace(/\/+$/, '');
  url = url.replace(/\/api\/v1$/i, '');
  return url;
}

export function hasPermission(perm: string): boolean {
  const { clinics, clinicId } = useSession.getState();
  const current = clinics.find((c) => c.clinic_id === clinicId);
  return !!current?.permissions.includes(perm);
}
