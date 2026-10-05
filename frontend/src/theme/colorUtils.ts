/**
 * Contraste WCAG y derivacion de color para la vista previa en vivo.
 * Espejo de backend/app/modules/branding/color_utils.py (misma formula),
 * necesario para que la pantalla de Apariencia responda al instante sin
 * ida y vuelta al servidor por cada ajuste de color.
 */

export function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace('#', '')
  return [
    parseInt(clean.slice(0, 2), 16),
    parseInt(clean.slice(2, 4), 16),
    parseInt(clean.slice(4, 6), 16),
  ]
}

export function rgbToHex([r, g, b]: [number, number, number]): string {
  const clamp = (c: number) => Math.max(0, Math.min(255, Math.round(c)))
  return (
    '#' +
    [clamp(r), clamp(g), clamp(b)]
      .map((c) => c.toString(16).padStart(2, '0'))
      .join('')
      .toUpperCase()
  )
}

function linearize(channel: number): number {
  const c = channel / 255
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
}

export function relativeLuminance(rgb: [number, number, number]): number {
  const [r, g, b] = rgb.map(linearize)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

export function contrastRatio(hexA: string, hexB: string): number {
  const la = relativeLuminance(hexToRgb(hexA))
  const lb = relativeLuminance(hexToRgb(hexB))
  const lighter = Math.max(la, lb)
  const darker = Math.min(la, lb)
  return (lighter + 0.05) / (darker + 0.05)
}

function rgbToHsl([r, g, b]: [number, number, number]): [number, number, number] {
  const rn = r / 255
  const gn = g / 255
  const bn = b / 255
  const max = Math.max(rn, gn, bn)
  const min = Math.min(rn, gn, bn)
  let h = 0
  let s = 0
  const l = (max + min) / 2

  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case rn:
        h = (gn - bn) / d + (gn < bn ? 6 : 0)
        break
      case gn:
        h = (bn - rn) / d + 2
        break
      default:
        h = (rn - gn) / d + 4
    }
    h /= 6
  }

  return [h, s, l]
}

function hueToRgb(p: number, q: number, t: number): number {
  let tt = t
  if (tt < 0) tt += 1
  if (tt > 1) tt -= 1
  if (tt < 1 / 6) return p + (q - p) * 6 * tt
  if (tt < 1 / 2) return q
  if (tt < 2 / 3) return p + (q - p) * (2 / 3 - tt) * 6
  return p
}

function hslToRgb([h, s, l]: [number, number, number]): [number, number, number] {
  if (s === 0) return [l * 255, l * 255, l * 255]
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s
  const p = 2 * l - q
  return [hueToRgb(p, q, h + 1 / 3) * 255, hueToRgb(p, q, h) * 255, hueToRgb(p, q, h - 1 / 3) * 255]
}

export function adjustLightness(hex: string, delta: number): string {
  const [h, s, l] = rgbToHsl(hexToRgb(hex))
  const newL = Math.max(0, Math.min(1, l + delta))
  return rgbToHex(hslToRgb([h, s, newL]))
}

/** --color-primary-hover: ~12% mas oscuro. */
export function deriveHover(primaryHex: string): string {
  return adjustLightness(primaryHex, -0.12)
}

/** --color-primary-soft: aclarado, para fondos suaves. */
export function deriveSoft(primaryHex: string): string {
  return adjustLightness(primaryHex, 0.38)
}

/** El texto de los botones primarios siempre es blanco (ver tokens.css). */
export const BUTTON_TEXT_COLOR = '#FFFFFF'

const WCAG_AA_TARGET = 4.5

export function suggestContrastingColor(
  fgHex: string,
  bgHex: string,
  target = WCAG_AA_TARGET,
): string {
  if (contrastRatio(fgHex, bgHex) >= target) return fgHex

  const bgIsLight = relativeLuminance(hexToRgb(bgHex)) > 0.5
  const direction = bgIsLight ? -1 : 1

  let candidate = fgHex
  for (let step = 1; step <= 25; step += 1) {
    candidate = adjustLightness(fgHex, direction * step * 0.04)
    if (contrastRatio(candidate, bgHex) >= target) return candidate
  }
  return candidate
}

export function meetsContrast(fgHex: string, bgHex: string, target = WCAG_AA_TARGET): boolean {
  return contrastRatio(fgHex, bgHex) >= target
}
