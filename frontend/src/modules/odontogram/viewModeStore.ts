import { create } from 'zustand'
import type { ViewMode } from './types'

/** Correccion UX (ronda 2.3, docs/clinica): el mismo componente `Odontograma`
 * se reusa tal cual en el tab principal "Odontograma" y embebido dentro de
 * "Historia Clinica Odontologica" (y "Historia Clinica Pediatrica") -- ambas
 * instancias ya comparten los mismos datos via TanStack Query
 * (['odontogram', patientId, atDate]), pero cada una mantenia su propio
 * `useState('permanente')` para `viewMode`, asi que cambiar la vista en un
 * lado no se reflejaba en el otro al entrar a esa pestana. Se extrae a un
 * estado compartido por paciente (mismo patron que searchStore.ts/theme/store.ts
 * con Zustand) para que ambas instancias lean y escriban el mismo valor. */

interface OdontogramViewModeState {
  viewModeByPatient: Record<string, ViewMode>
  getViewMode: (patientId: string) => ViewMode
  setViewMode: (patientId: string, mode: ViewMode) => void
}

export const useOdontogramViewModeStore = create<OdontogramViewModeState>((set, get) => ({
  viewModeByPatient: {},
  getViewMode: (patientId) => get().viewModeByPatient[patientId] ?? 'permanente',
  setViewMode: (patientId, mode) =>
    set((state) => ({ viewModeByPatient: { ...state.viewModeByPatient, [patientId]: mode } })),
}))
