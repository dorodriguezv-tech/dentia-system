import { renderHook, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAuthStore } from '../auth/store'
import type { VoiceConnection, VoiceConnectionOptions } from './connection'
import { useScreenContextStore } from './screenContext'
import { useVoiceStore } from './store'
import { useVoiceSession } from './useVoiceSession'

function LocationDisplay() {
  const location = useLocation()
  return <div data-testid="location-display">{`${location.pathname}|${JSON.stringify(location.state)}`}</div>
}

// useVoiceSession usa useNavigate/useLocation (13.2 "Navegacion") -- necesita
// un Router alrededor, igual que cualquier otro hook/componente que los use.
// LocationDisplay deja comprobar a donde navego sin tener que montar paginas
// reales.
function withRouter({ children }: { children: ReactNode }) {
  return (
    <MemoryRouter initialEntries={['/agenda']}>
      {children}
      <LocationDisplay />
    </MemoryRouter>
  )
}

function makeFakeConnect() {
  const sent: unknown[] = []
  const binarySent: ArrayBuffer[] = []
  let closedCount = 0
  let lastOptions: VoiceConnectionOptions | null = null
  const connect = vi.fn((options: VoiceConnectionOptions): VoiceConnection => {
    lastOptions = options
    return {
      send: (payload) => sent.push(payload),
      sendBinary: (data) => binarySent.push(data),
      close: () => {
        closedCount += 1
      },
    }
  })
  return {
    connect,
    sent,
    binarySent,
    get closedCount() {
      return closedCount
    },
    get lastOptions() {
      return lastOptions
    },
  }
}

function makeFakeStartCapture() {
  const stop = vi.fn()
  const startCapture = vi.fn().mockResolvedValue({ stop })
  return { startCapture, stop }
}

describe('useVoiceSession', () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: 'token-123', activeClinicId: 'clinic-abc' })
    useVoiceStore.setState({ state: 'disconnected', subtitle: null, activeInAnotherTab: false })
  })

  afterEach(() => {
    useAuthStore.setState({ accessToken: null, activeClinicId: null })
  })

  it('se conecta con el token y la sucursal activa una vez pasa la ventana de eleccion', async () => {
    const fakeConnect = makeFakeConnect()
    const fakeCapture = makeFakeStartCapture()

    const { unmount } = renderHook(() =>
      useVoiceSession({ connect: fakeConnect.connect, startCapture: fakeCapture.startCapture }),
      { wrapper: withRouter },
    )

    await waitFor(() => expect(fakeConnect.connect).toHaveBeenCalledTimes(1))
    expect(fakeConnect.connect.mock.calls[0][0]).toMatchObject({
      token: 'token-123',
      clinicId: 'clinic-abc',
    })

    unmount()
  })

  it('reenvia los mensajes "state" y "say" del servidor a useVoiceStore', async () => {
    const fakeConnect = makeFakeConnect()
    const fakeCapture = makeFakeStartCapture()

    const { unmount } = renderHook(() =>
      useVoiceSession({ connect: fakeConnect.connect, startCapture: fakeCapture.startCapture }),
      { wrapper: withRouter },
    )

    await waitFor(() => expect(fakeConnect.connect).toHaveBeenCalledTimes(1))
    const onMessage = fakeConnect.lastOptions?.onMessage
    expect(onMessage).toBeTypeOf('function')

    onMessage?.({ type: 'state', state: 'passive' })
    expect(useVoiceStore.getState().state).toBe('passive')

    onMessage?.({ type: 'say', text: '¿Sí?', audio: null })
    expect(useVoiceStore.getState().subtitle).toBe('¿Sí?')

    unmount()
  })

  it('empieza a capturar audio en cuanto llega el primer mensaje del servidor', async () => {
    const fakeConnect = makeFakeConnect()
    const fakeCapture = makeFakeStartCapture()

    const { unmount } = renderHook(() =>
      useVoiceSession({ connect: fakeConnect.connect, startCapture: fakeCapture.startCapture }),
      { wrapper: withRouter },
    )

    await waitFor(() => expect(fakeConnect.connect).toHaveBeenCalledTimes(1))
    fakeConnect.lastOptions?.onMessage({ type: 'state', state: 'passive' })

    await waitFor(() => expect(fakeCapture.startCapture).toHaveBeenCalledTimes(1))

    unmount()
  })

  it('toggleMute manda el mensaje "ui" correspondiente', async () => {
    const fakeConnect = makeFakeConnect()
    const fakeCapture = makeFakeStartCapture()

    const { result, unmount } = renderHook(() =>
      useVoiceSession({ connect: fakeConnect.connect, startCapture: fakeCapture.startCapture }),
      { wrapper: withRouter },
    )

    await waitFor(() => expect(fakeConnect.connect).toHaveBeenCalledTimes(1))

    result.current.toggleMute()
    expect(fakeConnect.sent).toContainEqual({ type: 'ui', action: 'mute' })

    result.current.toggleMute()
    expect(fakeConnect.sent).toContainEqual({ type: 'ui', action: 'unmute' })

    unmount()
  })

  it('no se conecta si no hay sesion activa', async () => {
    useAuthStore.setState({ accessToken: null, activeClinicId: null })
    const fakeConnect = makeFakeConnect()
    const fakeCapture = makeFakeStartCapture()

    const { unmount } = renderHook(() =>
      useVoiceSession({ connect: fakeConnect.connect, startCapture: fakeCapture.startCapture }),
      { wrapper: withRouter },
    )

    await new Promise((resolve) => setTimeout(resolve, 250))
    expect(fakeConnect.connect).not.toHaveBeenCalled()
    expect(useVoiceStore.getState().state).toBe('disconnected')

    unmount()
  })

  it('cierra la conexion y detiene la captura al desmontar', async () => {
    const fakeConnect = makeFakeConnect()
    const fakeCapture = makeFakeStartCapture()

    const { unmount } = renderHook(() =>
      useVoiceSession({ connect: fakeConnect.connect, startCapture: fakeCapture.startCapture }),
      { wrapper: withRouter },
    )

    await waitFor(() => expect(fakeConnect.connect).toHaveBeenCalledTimes(1))
    fakeConnect.lastOptions?.onMessage({ type: 'state', state: 'passive' })
    await waitFor(() => expect(fakeCapture.startCapture).toHaveBeenCalledTimes(1))

    unmount()

    expect(fakeConnect.closedCount).toBe(1)
    expect(fakeCapture.stop).toHaveBeenCalledTimes(1)
  })

  it('un ui_action "navigate" navega a la ruta indicada, con la pestaña por location.state', async () => {
    const fakeConnect = makeFakeConnect()
    const fakeCapture = makeFakeStartCapture()

    const { unmount } = renderHook(
      () => useVoiceSession({ connect: fakeConnect.connect, startCapture: fakeCapture.startCapture }),
      { wrapper: withRouter },
    )

    await waitFor(() => expect(fakeConnect.connect).toHaveBeenCalledTimes(1))
    fakeConnect.lastOptions?.onMessage({
      type: 'ui_action',
      action: 'navigate',
      payload: { path: '/pacientes/abc', tab: 'odontograma' },
    })

    await waitFor(() =>
      expect(screen.getByTestId('location-display')).toHaveTextContent(
        '/pacientes/abc|{"tab":"odontograma"}',
      ),
    )

    unmount()
  })

  it('manda el contexto de pantalla actual en cuanto se conecta', async () => {
    useScreenContextStore.setState({ patientId: 'pat-1', encounterId: 'enc-1', tab: 'resumen' })
    const fakeConnect = makeFakeConnect()
    const fakeCapture = makeFakeStartCapture()

    const { unmount } = renderHook(
      () => useVoiceSession({ connect: fakeConnect.connect, startCapture: fakeCapture.startCapture }),
      { wrapper: withRouter },
    )

    await waitFor(() => expect(fakeConnect.connect).toHaveBeenCalledTimes(1))
    fakeConnect.lastOptions?.onMessage({ type: 'state', state: 'passive' })

    await waitFor(() =>
      expect(fakeConnect.sent).toContainEqual({
        type: 'context',
        route: '/agenda',
        patient_id: 'pat-1',
        encounter_id: 'enc-1',
        tab: 'resumen',
      }),
    )

    unmount()
    useScreenContextStore.getState().clearScreenContext()
  })
})
