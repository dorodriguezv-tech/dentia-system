export interface ColorPalette {
  primary: string
  secondary: string
  accent: string
  bg: string
  surface: string
  border: string
  text: string
  text_muted: string
  success: string
  warning: string
  danger: string
}

export type RadiusCode = 'soft' | 'sharp'

export interface ContrastWarning {
  pair: string
  ratio: number
  suggested_color: string
}

export interface BrandingOut {
  display_name: string
  subtitle: string | null
  preset: string
  colors: ColorPalette
  dark_mode: boolean
  radius: RadiusCode
  logo_url: string | null
  favicon_url: string | null
  // W2 (docs/CAMBIOS_WEB_MARCA.md): logo_url ahora siempre trae algo que mostrar
  // (el propio o el de DENT-IA); este campo distingue si es el propio de verdad.
  has_custom_logo: boolean
  contrast_warnings: ContrastWarning[]
}

export interface BrandingUpdateInput {
  display_name: string
  subtitle: string | null
  preset: string
  colors?: ColorPalette
  dark_mode: boolean
  radius: RadiusCode
}
