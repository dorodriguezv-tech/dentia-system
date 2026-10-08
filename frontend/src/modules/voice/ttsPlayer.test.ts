import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { speak, stopSpeaking } from './ttsPlayer'

// jsdom no implementa la Web Speech API en absoluto -- se simula lo minimo que
// usa ttsPlayer.ts, ya que la verificacion real (voz audible) necesita un
// navegador de verdad.
class FakeSpeechSynthesisUtterance {
  text: string
  lang = ''
  voice: { lang: string } | null = null
  constructor(text: string) {
    this.text = text
  }
}

describe('ttsPlayer', () => {
  const originalSpeechSynthesis = window.speechSynthesis
  const originalUtterance = (
    window as unknown as { SpeechSynthesisUtterance?: unknown }
  ).SpeechSynthesisUtterance

  beforeEach(() => {
    ;(window as unknown as { SpeechSynthesisUtterance: unknown }).SpeechSynthesisUtterance =
      FakeSpeechSynthesisUtterance
    Object.defineProperty(window, 'speechSynthesis', {
      configurable: true,
      value: {
        getVoices: vi.fn().mockReturnValue([
          { lang: 'en-US', name: 'English' },
          { lang: 'es-MX', name: 'Spanish (Mexico)' },
        ]),
        speak: vi.fn(),
        cancel: vi.fn(),
      },
    })
  })

  afterEach(() => {
    Object.defineProperty(window, 'speechSynthesis', {
      configurable: true,
      value: originalSpeechSynthesis,
    })
    ;(window as unknown as { SpeechSynthesisUtterance: unknown }).SpeechSynthesisUtterance =
      originalUtterance
  })

  it('usa speechSynthesis cuando no hay audio del backend', () => {
    speak('¿Sí?', null)
    expect(window.speechSynthesis.cancel).toHaveBeenCalled()
    expect(window.speechSynthesis.speak).toHaveBeenCalledTimes(1)
    const utterance = vi.mocked(window.speechSynthesis.speak).mock.calls[0][0]
    expect(utterance.text).toBe('¿Sí?')
    expect(utterance.voice?.lang).toBe('es-MX')
  })

  it('cancela cualquier habla en curso', () => {
    stopSpeaking()
    expect(window.speechSynthesis.cancel).toHaveBeenCalled()
  })
})
