import { create } from 'zustand'
import { resolveApiAssetUrl } from '../api/client'
import * as api from '../modules/branding/api'
import type { BrandingOut, ColorPalette, RadiusCode } from '../modules/branding/types'
import { deriveHover, deriveSoft, suggestContrastingColor } from './colorUtils'
import { DARK_OVERRIDES, RADIUS_VALUES, findPreset } from './presets'

interface ThemeState {
  branding: BrandingOut | null
  loading: boolean
  load: () => Promise<void>
  applyPreview: (colors: ColorPalette, darkMode: boolean, radius: RadiusCode, presetCode: string) => void
  applySaved: (branding: BrandingOut) => void
  resetPreviewToSaved: () => void
}

/** Modo oscuro (docs/CAMBIOS_WEB_MARCA.md W6): si el preset trae `dark_primary`,
 * se usa en vez de "primary"; si no, se aclara hasta 4.5:1 sobre la superficie oscura. */
function effectivePrimary(primary: string, darkMode: boolean, presetCode: string): string {
  if (!darkMode) return primary
  const dark = findPreset(presetCode)?.dark_primary
  return dark ?? suggestContrastingColor(primary, DARK_OVERRIDES.surface, 4.5)
}

function applyToDom(colors: ColorPalette, darkMode: boolean, radius: RadiusCode, presetCode: string): void {
  const root = document.documentElement.style
  const effective = darkMode
    ? { ...colors, ...DARK_OVERRIDES, primary: effectivePrimary(colors.primary, darkMode, presetCode) }
    : colors

  root.setProperty('--color-primary', effective.primary)
  root.setProperty('--color-primary-hover', deriveHover(effective.primary))
  root.setProperty('--color-primary-soft', deriveSoft(effective.primary))
  root.setProperty('--color-secondary', effective.secondary)
  root.setProperty('--color-accent', effective.accent)
  root.setProperty('--color-bg', effective.bg)
  root.setProperty('--color-surface', effective.surface)
  root.setProperty('--color-border', effective.border)
  root.setProperty('--color-text', effective.text)
  root.setProperty('--color-text-muted', effective.text_muted)
  root.setProperty('--color-success', effective.success)
  root.setProperty('--color-warning', effective.warning)
  root.setProperty('--color-danger', effective.danger)
  root.setProperty('--color-danger-soft', deriveSoft(effective.danger))
  root.setProperty('--radius', RADIUS_VALUES[radius])
}

function applyFavicon(faviconUrl: string | null): void {
  if (!faviconUrl) return
  const link =
    document.querySelector<HTMLLinkElement>('link[rel="icon"]') ??
    document.head.appendChild(document.createElement('link'))
  link.rel = 'icon'
  link.href = resolveApiAssetUrl(faviconUrl)
}

export const useThemeStore = create<ThemeState>((set, get) => ({
  branding: null,
  loading: true,

  async load() {
    try {
      const branding = await api.getBranding()
      set({ branding, loading: false })
      applyToDom(branding.colors, branding.dark_mode, branding.radius, branding.preset)
      applyFavicon(branding.favicon_url)
    } catch {
      set({ loading: false })
    }
  },

  applyPreview(colors, darkMode, radius, presetCode) {
    applyToDom(colors, darkMode, radius, presetCode)
  },

  applySaved(branding) {
    set({ branding })
    applyToDom(branding.colors, branding.dark_mode, branding.radius, branding.preset)
    applyFavicon(branding.favicon_url)
  },

  resetPreviewToSaved() {
    const branding = get().branding
    if (branding) applyToDom(branding.colors, branding.dark_mode, branding.radius, branding.preset)
  },
}))
