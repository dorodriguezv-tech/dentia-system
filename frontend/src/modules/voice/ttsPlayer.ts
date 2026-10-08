/** Fase 13 ("Dentia"): reproduce lo que Dentia dice. El backend manda WAV en
 * base64 cuando Piper esta configurado e instalado (app/voice/tts.py); si no
 * (`audio` null -- Piper no instalado, o VOICE_TTS_ENGINE distinto), cae al
 * respaldo documentado en el diseno (sec. 5): `speechSynthesis` del navegador,
 * eligiendo una voz femenina en espanol si el navegador ofrece alguna. */

function pickSpanishVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | undefined {
  const spanishVoices = voices.filter((v) => v.lang.toLowerCase().startsWith('es'))
  const mexican = spanishVoices.find((v) => v.lang.toLowerCase() === 'es-mx')
  return mexican ?? spanishVoices[0] ?? voices[0]
}

export function speak(text: string, audioBase64: string | null): void {
  if (audioBase64) {
    const audio = new Audio(`data:audio/wav;base64,${audioBase64}`)
    void audio.play()
    return
  }

  if (typeof window === 'undefined' || !window.speechSynthesis) return
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'es-MX'
  const voice = pickSpanishVoice(window.speechSynthesis.getVoices())
  if (voice) utterance.voice = voice
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(utterance)
}

export function stopSpeaking(): void {
  if (typeof window !== 'undefined' && window.speechSynthesis) window.speechSynthesis.cancel()
}
