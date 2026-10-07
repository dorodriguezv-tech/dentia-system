import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { RouterProvider } from 'react-router-dom'
import { useAuthStore } from '../modules/auth/store'
import { ThemeProvider } from '../theme/ThemeProvider'
import { ErrorToast } from './ErrorToast'
import { createGlobalMutationCache } from './globalMutationErrorHandling'
import { router } from './router'

const queryClient = new QueryClient({ mutationCache: createGlobalMutationCache() })

export function AppProviders() {
  const bootstrap = useAuthStore((s) => s.bootstrap)
  // StrictMode (main.tsx) monta/desmonta/remonta en desarrollo para detectar efectos
  // sin limpieza -- sin esta bandera, bootstrap() (que llama /auth/refresh) se dispara
  // dos veces en cada carga, duplicando la llamada (y, con un refresh token vencido,
  // duplicando el 401 en el log del backend).
  const didBootstrap = useRef(false)

  useEffect(() => {
    if (didBootstrap.current) return
    didBootstrap.current = true
    bootstrap()
  }, [bootstrap])

  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
        <ErrorToast />
      </QueryClientProvider>
    </ThemeProvider>
  )
}
