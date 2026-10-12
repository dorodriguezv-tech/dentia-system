import { useSession } from '@/store/session';

import type { ApiErrorBody, TokenPair } from './types';

/**
 * Cliente HTTP de la app.
 *
 * - Agrega `Authorization: Bearer` y `X-Clinic-Id` (ABAC por sucursal, docs/02 §5.1).
 * - Si la API responde 401, intenta UNA vez `/auth/refresh` (con rotación) y repite.
 *   Varias peticiones simultáneas comparten el mismo refresh (single-flight), porque
 *   el backend revoca el refresh anterior en cada rotación: dos refresh en paralelo
 *   harían que el segundo falle y cerrarían la sesión sin motivo.
 * - Timeout configurable: /ai/interpret puede tardar hasta 120 s con Ollama local.
 */

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string | undefined,
    message: string,
    public body?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class NetworkError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'NetworkError';
  }
}

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

interface RequestOptions {
  method?: Method;
  body?: unknown;
  form?: FormData;
  query?: Record<string, string | number | boolean | undefined | null>;
  auth?: boolean; // default true
  timeoutMs?: number; // default 20 s
  retryOn401?: boolean; // interno
}

let refreshInFlight: Promise<boolean> | null = null;

export function apiBase(): string {
  const server = useSession.getState().serverUrl;
  if (!server) throw new NetworkError('No hay servidor configurado.');
  return `${server}/api/v1`;
}

export async function api<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, form, query, auth = true, timeoutMs = 20_000, retryOn401 = true } = opts;
  const state = useSession.getState();

  const url = new URL(apiBase() + path);
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v));
    }
  }

  const headers: Record<string, string> = {
    Accept: 'application/json',
    // Le dice al backend que es la app móvil (útil para que /auth/refresh responda
    // el refresh token en el cuerpo en vez de una cookie; ver docs/05 §7).
    'X-Client': 'dentia-mobile',
  };
  if (auth && state.accessToken) headers.Authorization = `Bearer ${state.accessToken}`;
  if (auth && state.clinicId) headers['X-Clinic-Id'] = state.clinicId;

  let payload: BodyInit | undefined;
  if (form) {
    payload = form; // fetch pone el boundary multipart solo
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(url.toString(), { method, headers, body: payload, signal: controller.signal });
  } catch (e) {
    const aborted = e instanceof Error && e.name === 'AbortError';
    throw new NetworkError(
      aborted
        ? 'El servidor tardó demasiado en responder.'
        : 'No se pudo conectar con el servidor de la clínica. ¿Estás en la red de la clínica o en la VPN?',
    );
  } finally {
    clearTimeout(timer);
  }

  if (res.status === 401 && auth && retryOn401) {
    const ok = await refreshAccessToken();
    if (ok) return api<T>(path, { ...opts, retryOn401: false });
    await useSession.getState().clear();
    throw new ApiError(401, 'SESSION_EXPIRED', 'Tu sesión expiró. Vuelve a iniciar sesión.');
  }

  if (!res.ok) {
    let parsed: ApiErrorBody | undefined;
    try {
      parsed = (await res.json()) as ApiErrorBody;
    } catch {
      /* cuerpo vacío o no JSON */
    }
    const { code, message } = describeError(res.status, parsed);
    throw new ApiError(res.status, code, message, parsed);
  }

  if (res.status === 204) return undefined as T;
  const ct = res.headers.get('content-type') ?? '';
  if (ct.includes('application/json')) return (await res.json()) as T;
  return (await res.text()) as unknown as T;
}

export async function refreshAccessToken(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  refreshInFlight = (async () => {
    const { refreshToken, setTokens } = useSession.getState();
    if (!refreshToken) return false;
    try {
      const pair = await api<TokenPair>('/auth/refresh', {
        method: 'POST',
        body: { refresh_token: refreshToken },
        auth: false,
        retryOn401: false,
      });
      await setTokens(pair.access_token, pair.refresh_token);
      return true;
    } catch {
      return false;
    }
  })();
  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

function describeError(status: number, body?: ApiErrorBody): { code?: string; message: string } {
  const d = body?.detail;
  if (typeof d === 'string') return { code: body?.code, message: d };
  if (d && typeof d === 'object' && 'message' in d) {
    const obj = d as { code?: string; message?: string };
    return { code: obj.code, message: obj.message ?? `Error ${status}` };
  }
  if (status === 403) return { code: 'FORBIDDEN', message: 'No tienes permiso para esta acción.' };
  if (status === 404) return { code: 'NOT_FOUND', message: 'No se encontró el recurso.' };
  if (status === 409) return { code: 'CONFLICT', message: 'Hay un conflicto con otro registro (por ejemplo, un horario ocupado).' };
  if (status === 503) return { code: 'UNAVAILABLE', message: 'El servicio no está disponible en este momento.' };
  return { code: body?.code, message: `Error del servidor (${status}).` };
}

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError || e instanceof NetworkError) return e.message;
  if (e instanceof Error) return e.message;
  return 'Ocurrió un error inesperado.';
}
