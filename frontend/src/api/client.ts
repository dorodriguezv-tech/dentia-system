const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

export interface ApiError {
  code: string
  message: string
  details?: unknown
}

export class ApiRequestError extends Error {
  code: string
  details?: unknown
  status: number

  constructor(status: number, error: ApiError) {
    super(error.message)
    this.code = error.code
    this.details = error.details
    this.status = status
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  signal?: AbortSignal
  /** false para /auth/login y /auth/refresh: no mandan ni requieren sesion. */
  auth?: boolean
}

interface SessionHooks {
  getAccessToken: () => string | null
  getClinicId: () => string | null
  /** Intenta renovar la sesion con el refresh token. true si lo logro. */
  refreshSession: () => Promise<boolean>
  onSessionExpired: () => void
}

let sessionHooks: SessionHooks | null = null

/** Inyectado por el store de autenticacion al arrancar la app (evita import circular). */
export function setSessionHooks(hooks: SessionHooks): void {
  sessionHooks = hooks
}

async function doFetch(path: string, options: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }

  if (options.auth !== false && sessionHooks) {
    const token = sessionHooks.getAccessToken()
    if (token) headers.Authorization = `Bearer ${token}`
    const clinicId = sessionHooks.getClinicId()
    if (clinicId) headers['X-Clinic-Id'] = clinicId
  }

  return fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  })
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response = await doFetch(path, options)

  if (response.status === 401 && options.auth !== false && sessionHooks) {
    const refreshed = await sessionHooks.refreshSession()
    if (refreshed) {
      response = await doFetch(path, options)
    } else {
      sessionHooks.onSessionExpired()
    }
  }

  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as ApiError | null
    throw new ApiRequestError(
      response.status,
      error ?? { code: 'UNKNOWN_ERROR', message: 'Error de comunicacion con el servidor' },
    )
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}
