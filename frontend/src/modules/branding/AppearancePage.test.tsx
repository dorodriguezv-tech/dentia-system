import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AppearancePage } from './AppearancePage'
import { useThemeStore } from '../../theme/store'
import { PRESETS } from '../../theme/presets'
import type { BrandingOut } from './types'

vi.mock('./api')

const initialBranding: BrandingOut = {
  display_name: 'Clinica Demo',
  subtitle: null,
  preset: 'menta_clinica',
  colors: {
    primary: '#2BB3A3',
    secondary: '#4A90C2',
    accent: '#F2A65A',
    bg: '#F7FAFA',
    surface: '#FFFFFF',
    border: '#DCE6E5',
    text: '#1F2D2B',
    text_muted: '#5E6E6C',
    success: '#3BA55C',
    warning: '#E0A100',
    danger: '#D64545',
  },
  dark_mode: false,
  radius: 'soft',
  logo_url: null,
  favicon_url: null,
  contrast_warnings: [],
}

const initialThemeState = useThemeStore.getState()

describe('AppearancePage', () => {
  beforeEach(() => {
    useThemeStore.setState(initialThemeState, true)
    useThemeStore.setState({ branding: initialBranding, loading: false })
  })

  it('muestra un cargando mientras no hay branding', () => {
    useThemeStore.setState({ branding: null })
    render(<AppearancePage />)
    expect(screen.getByText('Cargando apariencia...')).toBeInTheDocument()
  })

  it('cambiar de preset actualiza los selectores de color', async () => {
    render(<AppearancePage />)

    const azulSereno = PRESETS.find((p) => p.code === 'azul_sereno')!
    await userEvent.click(screen.getByRole('button', { name: new RegExp(azulSereno.name) }))

    const primaryInput = screen.getByLabelText('Primario') as HTMLInputElement
    expect(primaryInput.value.toUpperCase()).toBe(azulSereno.primary)
  })

  it('editar un color a mano quita el preset activo (personalizado)', () => {
    render(<AppearancePage />)

    const mentaButton = screen.getByRole('button', { name: /Menta clinica/ })
    expect(mentaButton.className).toMatch(/active/)

    const primaryInput = screen.getByLabelText('Primario') as HTMLInputElement
    fireEvent.change(primaryInput, { target: { value: '#123456' } })

    expect(mentaButton.className).not.toMatch(/active/)
  })
})
