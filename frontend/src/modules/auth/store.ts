import { create } from 'zustand'
import { setSessionHooks } from '../../api/client'
import * as api from './api'
import type { MyClinicOut, TokenResponse, UserOut } from './types'

const REFRESH_TOKEN_KEY = 'dentia.refresh_token'
const CLINIC_ID_KEY = 'dentia.active_clinic_id'

type AuthStatus = 'checking' | 'anonymous' | 'authenticated'

interface AuthState {
  status: AuthStatus
  accessToken: string | null
  refreshToken: string | null
  user: UserOut | null
  clinics: MyClinicOut[]
  activeClinicId: string | null
  applySession: (tokens: TokenResponse) => Promise<void>
  loadClinics: () => Promise<MyClinicOut[]>
  selectClinic: (clinicId: string) => void
  refreshUser: () => Promise<void>
  logout: () => Promise<void>
  bootstrap: () => Promise<void>
}

function readStoredRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_TOKEN_KEY)
  } catch {
    return null
  }
}

function persistRefreshToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(REFRESH_TOKEN_KEY, token)
    else localStorage.removeItem(REFRESH_TOKEN_KEY)
  } catch {
    // almacenamiento no disponible (modo privado); la sesion no sobrevive un recargo
  }
}

function persistActiveClinicId(clinicId: string | null): void {
  try {
    if (clinicId) localStorage.setItem(CLINIC_ID_KEY, clinicId)
    else localStorage.removeItem(CLINIC_ID_KEY)
  } catch {
    // ver persistRefreshToken
  }
}

export const useAuthStore = create<AuthState>((set, get) => ({
  status: 'checking',
  accessToken: null,
  refreshToken: null,
  user: null,
  clinics: [],
  activeClinicId: null,

  async applySession(tokens) {
    persistRefreshToken(tokens.refresh_token)
    set({
      status: 'authenticated',
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      user: tokens.user,
    })
    await get().loadClinics()
  },

  async loadClinics() {
    const clinics = await api.getMyClinics()
    let activeClinicId = get().activeClinicId
    if (!activeClinicId || !clinics.some((c) => c.clinic.id === activeClinicId)) {
      activeClinicId = clinics.length === 1 ? clinics[0].clinic.id : null
    }
    persistActiveClinicId(activeClinicId)
    set({ clinics, activeClinicId })
    return clinics
  },

  selectClinic(clinicId) {
    persistActiveClinicId(clinicId)
    set({ activeClinicId: clinicId })
  },

  async refreshUser() {
    const user = await api.getMe()
    set({ user })
  },

  async logout() {
    const token = get().refreshToken
    persistRefreshToken(null)
    persistActiveClinicId(null)
    set({
      status: 'anonymous',
      accessToken: null,
      refreshToken: null,
      user: null,
      clinics: [],
      activeClinicId: null,
    })
    if (token) {
      await api.logout(token).catch(() => undefined)
    }
  },

  async bootstrap() {
    const storedRefreshToken = readStoredRefreshToken()
    if (!storedRefreshToken) {
      set({ status: 'anonymous' })
      return
    }

    set({ activeClinicId: localStorage.getItem(CLINIC_ID_KEY) })
    try {
      const tokens = await api.refresh(storedRefreshToken)
      await get().applySession(tokens)
    } catch {
      persistRefreshToken(null)
      set({ status: 'anonymous' })
    }
  },
}))

setSessionHooks({
  getAccessToken: () => useAuthStore.getState().accessToken,
  getClinicId: () => useAuthStore.getState().activeClinicId,
  async refreshSession() {
    const token = useAuthStore.getState().refreshToken
    if (!token) return false
    try {
      const tokens = await api.refresh(token)
      await useAuthStore.getState().applySession(tokens)
      return true
    } catch {
      return false
    }
  },
  onSessionExpired() {
    void useAuthStore.getState().logout()
  },
})
