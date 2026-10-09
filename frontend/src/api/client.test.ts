import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiRequest, setSessionHooks } from './client'

/**
 * Bug real visto en vivo: con el access token expirado, dos peticiones
 * concurrentes (p.ej. el tablero de inicio pidiendo varias secciones a la
 * vez) reciben 401 casi al mismo tiempo. Sin deduplicar, cada una llamaba a
 * su propio refreshSession() -- con un refresh token de un solo uso eso
 * colisiona y deja la pantalla en "Cargando..." para siempre. Distinto del
 * bug de doble-bootstrap de StrictMode que ya corrigio AppProviders (ese es
 * solo al montar la app una vez).
 */
describe('apiRequest ante 401 concurrentes', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('comparte un solo refreshSession() entre peticiones concurrentes', async () => {
    const callsByUrl = new Map<string, number>()
    vi.stubGlobal(
      'fetch',
      vi.fn(async (url: string) => {
        const count = (callsByUrl.get(url) ?? 0) + 1
        callsByUrl.set(url, count)
        if (count === 1) {
          return new Response(JSON.stringify({ code: 'UNAUTHENTICATED', message: 'expirado' }), {
            status: 401,
          })
        }
        return new Response(JSON.stringify({ ok: true }), { status: 200 })
      }),
    )

    const refreshSession = vi.fn(async () => {
      await new Promise((resolve) => setTimeout(resolve, 20))
      return true
    })

    setSessionHooks({
      getAccessToken: () => 'token-vencido',
      getClinicId: () => 'clinica-1',
      refreshSession,
      onSessionExpired: vi.fn(),
    })

    await Promise.all([apiRequest('/a'), apiRequest('/b')])

    expect(refreshSession).toHaveBeenCalledTimes(1)
  })
})
