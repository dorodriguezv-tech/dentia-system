/** Captura de microfono para Dentia (13.1 "Base de voz", diseno sec. 5):
 * `getUserMedia` + `AudioWorklet` a 16 kHz mono, frames PCM16 de ~20-30 ms.
 *
 * El procesador del AudioWorklet se carga desde un Blob URL (en vez de un
 * archivo estatico aparte) para no depender de configurar una ruta publica en
 * Vite -- es jecsp (JS puro, sin imports) y vive en AudioWorkletGlobalScope,
 * un entorno distinto al del resto de la app.
 *
 * No se puede probar de verdad en jsdom (no hay AudioContext/getUserMedia reales
 * ahi) -- ver useVoiceSession.ts, que inyecta un doble de este modulo en pruebas.
 * La verificacion real ("decir Dentia enciende el orbe") requiere un navegador
 * con microfono.
 */

const FRAME_SAMPLES = 480 // ~30 ms a 16 kHz

const WORKLET_SOURCE = `
class PcmCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this._buffer = []
    this._bufferLength = 0
  }

  process(inputs) {
    const input = inputs[0]
    if (!input || input.length === 0) return true
    const channel = input[0]
    if (!channel) return true

    this._buffer.push(channel.slice())
    this._bufferLength += channel.length

    while (this._bufferLength >= ${FRAME_SAMPLES}) {
      const frame = new Float32Array(${FRAME_SAMPLES})
      let offset = 0
      while (offset < ${FRAME_SAMPLES}) {
        const chunk = this._buffer[0]
        const needed = ${FRAME_SAMPLES} - offset
        if (chunk.length <= needed) {
          frame.set(chunk, offset)
          offset += chunk.length
          this._buffer.shift()
        } else {
          frame.set(chunk.subarray(0, needed), offset)
          this._buffer[0] = chunk.subarray(needed)
          offset += needed
        }
      }
      this._bufferLength -= ${FRAME_SAMPLES}

      const pcm16 = new Int16Array(${FRAME_SAMPLES})
      for (let i = 0; i < ${FRAME_SAMPLES}; i++) {
        const sample = Math.max(-1, Math.min(1, frame[i]))
        pcm16[i] = sample < 0 ? sample * 32768 : sample * 32767
      }
      this.port.postMessage(pcm16.buffer, [pcm16.buffer])
    }
    return true
  }
}
registerProcessor('pcm-capture', PcmCaptureProcessor)
`

export interface AudioCaptureHandle {
  stop: () => void
}

export async function startAudioCapture(
  onFrame: (frame: ArrayBuffer) => void,
): Promise<AudioCaptureHandle> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  })

  // Chrome/Firefox honran sampleRate al crear el contexto; Safari puede
  // ignorarlo (quedaria a 44.1/48 kHz) -- remuestreo manual queda pendiente si
  // se necesita soportar Safari (ver docs/PENDIENTES_CLINICOS.md).
  const audioContext = new AudioContext({ sampleRate: 16_000 })
  const workletUrl = URL.createObjectURL(
    new Blob([WORKLET_SOURCE], { type: 'application/javascript' }),
  )
  await audioContext.audioWorklet.addModule(workletUrl)
  URL.revokeObjectURL(workletUrl)

  const source = audioContext.createMediaStreamSource(stream)
  const node = new AudioWorkletNode(audioContext, 'pcm-capture')
  node.port.onmessage = (event: MessageEvent<ArrayBuffer>) => onFrame(event.data)
  source.connect(node)

  return {
    stop: () => {
      node.port.onmessage = null
      source.disconnect()
      node.disconnect()
      for (const track of stream.getTracks()) track.stop()
      void audioContext.close()
    },
  }
}
