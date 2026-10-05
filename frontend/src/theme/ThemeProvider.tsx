import { useEffect, type ReactNode } from 'react'
import { useThemeStore } from './store'

/** Lee GET /api/v1/branding al iniciar y escribe las variables de tema en <html>. */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const load = useThemeStore((s) => s.load)

  useEffect(() => {
    load()
  }, [load])

  return children
}
