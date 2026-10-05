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
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? 'GET',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    signal: options.signal,
  })

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
