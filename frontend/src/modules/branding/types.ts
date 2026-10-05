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
