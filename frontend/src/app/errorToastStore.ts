import { create } from 'zustand'

interface ErrorToastState {
  message: string | null
  show: (message: string) => void
  dismiss: () => void
}

/** A4 (red de seguridad): un mensaje de error de cualquier mutacion que no maneje su
 * propio error (ver app/providers.tsx, MutationCache) termina aqui, para que ningun
 * boton "Agregar" falle en silencio en ninguna pantalla. */
export const useErrorToastStore = create<ErrorToastState>((set) => ({
  message: null,
  show: (message) => set({ message }),
  dismiss: () => set({ message: null }),
}))
