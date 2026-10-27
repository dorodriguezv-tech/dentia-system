export type LogoSide = 'left' | 'right'

export interface DocumentSettingsOut {
  institutional_title: string | null
  place_label: string | null
  logo_left_url: string | null
  logo_right_url: string | null
  has_logo_left: boolean
  has_logo_right: boolean
}

export interface DocumentSettingsUpdateInput {
  institutional_title?: string | null
  place_label?: string | null
}
