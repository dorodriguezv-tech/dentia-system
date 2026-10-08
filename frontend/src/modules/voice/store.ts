import { create } from 'zustand'
import type { VoiceConnectionState } from './types'

interface VoiceState {
  state: VoiceConnectionState
  subtitle: string | null
  /** true si el microfono lo tiene OTRA pestana (BroadcastChannel) -- esta
   * pestana muestra el orbe gris "activo en otra pestana" (sec. 7.1 del diseno). */
  activeInAnotherTab: boolean
  setState: (state: VoiceConnectionState) => void
  setSubtitle: (subtitle: string | null) => void
  setActiveInAnotherTab: (value: boolean) => void
}

export const useVoiceStore = create<VoiceState>((set) => ({
  state: 'disconnected',
  subtitle: null,
  activeInAnotherTab: false,
  setState: (state) => set({ state }),
  setSubtitle: (subtitle) => set({ subtitle }),
  setActiveInAnotherTab: (activeInAnotherTab) => set({ activeInAnotherTab }),
}))
