import { useRef, useState } from 'react'
import styles from './SignaturePad.module.css'

/**
 * Firma en pantalla tactil (docs/09 Fase 9): un <canvas> que dibuja con eventos de
 * puntero (unifica mouse y touch) y exporta un PNG en base64 cuando hay trazo. Sin
 * libreria externa: solo trazos, sin necesidad de deshacer/curvas suaves.
 */
export function SignaturePad({ onChange }: { onChange: (dataUrl: string | null) => void }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const drawingRef = useRef(false)
  const [hasStroke, setHasStroke] = useState(false)

  function getContext(): CanvasRenderingContext2D | null {
    return canvasRef.current?.getContext('2d') ?? null
  }

  function pointerPosition(e: React.PointerEvent<HTMLCanvasElement>): { x: number; y: number } {
    const rect = e.currentTarget.getBoundingClientRect()
    return { x: e.clientX - rect.left, y: e.clientY - rect.top }
  }

  function handlePointerDown(e: React.PointerEvent<HTMLCanvasElement>) {
    const ctx = getContext()
    if (!ctx) return
    e.currentTarget.setPointerCapture(e.pointerId)
    drawingRef.current = true
    const { x, y } = pointerPosition(e)
    ctx.beginPath()
    ctx.moveTo(x, y)
  }

  function handlePointerMove(e: React.PointerEvent<HTMLCanvasElement>) {
    if (!drawingRef.current) return
    const ctx = getContext()
    if (!ctx) return
    const { x, y } = pointerPosition(e)
    ctx.lineWidth = 2
    ctx.lineCap = 'round'
    // El canvas no entiende var(--color-...): hay que resolver la variable CSS a un
    // color real en tiempo de ejecucion (CLAUDE.md sec. 6 sigue cumpliendose porque el
    // valor viene del tema, no esta fijo en el codigo).
    ctx.strokeStyle = getComputedStyle(document.documentElement)
      .getPropertyValue('--color-text')
      .trim()
    ctx.lineTo(x, y)
    ctx.stroke()
  }

  function handlePointerUp() {
    if (!drawingRef.current) return
    drawingRef.current = false
    setHasStroke(true)
    const canvas = canvasRef.current
    onChange(canvas ? canvas.toDataURL('image/png') : null)
  }

  function handleClear() {
    const canvas = canvasRef.current
    const ctx = getContext()
    if (!canvas || !ctx) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    setHasStroke(false)
    onChange(null)
  }

  return (
    <div className={styles.wrapper}>
      <canvas
        ref={canvasRef}
        width={400}
        height={150}
        role="img"
        aria-label={
          hasStroke
            ? 'Firma capturada'
            : 'Area para firmar con el mouse o el dedo -- requiere un dispositivo senalador'
        }
        className={styles.canvas}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
      />
      <div className={styles.actions}>
        <span>{hasStroke ? 'Firma capturada' : 'Firme con el mouse o el dedo'}</span>
        <button className={styles.linkButton} type="button" onClick={handleClear}>
          Borrar firma
        </button>
      </div>
    </div>
  )
}
