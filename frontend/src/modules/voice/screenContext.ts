import { create } from 'zustand'

/** Fase 13 ("Dentia"), 13.2 "Navegacion": lo que cada pantalla declara sobre si
 * misma (paciente activo, atencion, pestaña) para que Dentia sepa de que
 * paciente se habla sin que la orden lo repita ("abre el odontograma" sin
 * decir el nombre). La ruta la actualiza useVoiceSession.ts solo (via
 * react-router), independiente de esto -- no toda pantalla tiene paciente. */

interface ScreenContextState {
  patientId: string | null
  encounterId: string | null
  tab: string | null
  setScreenContext: (context: {
    patientId?: string | null
    encounterId?: string | null
    tab?: string | null
  }) => void
  clearScreenContext: () => void
}

export const useScreenContextStore = create<ScreenContextState>((set) => ({
  patientId: null,
  encounterId: null,
  tab: null,
  setScreenContext: (context) =>
    set({
      patientId: context.patientId ?? null,
      encounterId: context.encounterId ?? null,
      tab: context.tab ?? null,
    }),
  clearScreenContext: () => set({ patientId: null, encounterId: null, tab: null }),
}))
