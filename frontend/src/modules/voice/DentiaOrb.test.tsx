import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { DentiaOrb } from './DentiaOrb'
import { useVoiceStore } from './store'

const toggleMute = vi.fn()
vi.mock('./useVoiceSession', () => ({
  useVoiceSession: () => ({ toggleMute }),
}))

describe('DentiaOrb', () => {
  beforeEach(() => {
    toggleMute.mockReset()
    useVoiceStore.setState({ state: 'disconnected', subtitle: null, activeInAnotherTab: false })
  })

  it('no se muestra si esta desconectado y no esta activo en otra pestaña', () => {
    render(<DentiaOrb />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('se muestra en escucha pasiva con su etiqueta', () => {
    useVoiceStore.setState({ state: 'passive' })
    render(<DentiaOrb />)
    expect(
      screen.getByRole('button', { name: 'Dentia escuchando en segundo plano' }),
    ).toBeInTheDocument()
  })

  it('muestra el subtitulo cuando Dentia dice algo', () => {
    useVoiceStore.setState({ state: 'speaking', subtitle: '¿Sí?' })
    render(<DentiaOrb />)
    expect(screen.getByRole('status')).toHaveTextContent('¿Sí?')
  })

  it('clic en el orbe llama a toggleMute', async () => {
    useVoiceStore.setState({ state: 'passive' })
    render(<DentiaOrb />)
    await userEvent.click(screen.getByRole('button'))
    expect(toggleMute).toHaveBeenCalledTimes(1)
  })

  it('se muestra deshabilitado como "activo en otra pestaña"', () => {
    useVoiceStore.setState({ state: 'disconnected', activeInAnotherTab: true })
    render(<DentiaOrb />)
    const button = screen.getByRole('button', { name: 'Dentia activa en otra pestaña' })
    expect(button).toBeDisabled()
  })
})
