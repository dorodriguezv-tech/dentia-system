import type { ToothVisualType } from './toothRules'

/**
 * Geometria decorativa (no clicable) de la silueta anatomica corona+raiz del odontograma
 * (Fase B). Todo lo que devuelve este archivo son cadenas `d` de `<path>`/posiciones de
 * `<circle>`, nunca `<rect>` -- Tooth.tsx sigue dibujando las 5 superficies clicables con
 * exactamente los mismos 5 `<rect>` de siempre (mismo orden en el DOM: top, bottom, left,
 * right, center), asi que Odontograma.test.tsx (`querySelectorAll('rect')[4]`) y el
 * contrato con Arch/FindingQuickMenu/ToothHistoryPanel no cambian. Esta capa solo se
 * dibuja detras/alrededor de esos `<rect>` para que la pieza se vea como un diente real
 * (corona con cuspides + raiz que se afina) en vez del cuadrado abstracto anterior.
 *
 * Sistema de coordenadas local de la corona: 0..44 en x y en y, igual que el viewBox
 * historico de Tooth.tsx. `cuspEdge` indica cual borde horizontal es el oclusal/incisal
 * (el que se ve "mordiendo", con cuspides) para esa arcada -- ver Tooth.tsx para el porque:
 * arcada superior = cuspides abajo (la raiz queda arriba, hacia la encia/fuera de la
 * arcada); arcada inferior = cuspides arriba (la raiz queda abajo).
 */

const CROWN_WIDTH_BY_TYPE: Record<ToothVisualType, number> = {
  anterior: 26,
  premolar: 34,
  molar: 44,
}

const CUSPS_BY_TYPE: Record<ToothVisualType, number> = {
  anterior: 1,
  premolar: 2,
  molar: 4,
}

const CORNER_R = 6
const CROWN_CENTER_X = 22

export function crownWidth(type: ToothVisualType): number {
  return CROWN_WIDTH_BY_TYPE[type]
}

/** Factor de escala horizontal (centrado en x=22) para encoger el grupo de los 5 `<rect>`
 * clicables a lo ancho de la corona segun el tipo de pieza, sin tocar sus coordenadas ni
 * su orden -- una pieza anterior se ve mas angosta que un molar, como en la vida real. */
export function crownScaleX(type: ToothVisualType): number {
  return crownWidth(type) / 44
}

/** Contorno decorativo de la corona: un cuerpo redondeado en el borde cervical (pegado a
 * la raiz) con un borde de cuspides onduladas en el borde oclusal/incisal opuesto. */
export function crownOutlinePath(type: ToothVisualType, cuspEdge: 'top' | 'bottom'): string {
  const width = crownWidth(type)
  const left = CROWN_CENTER_X - width / 2 + 2
  const right = CROWN_CENTER_X + width / 2 - 2
  const cusps = CUSPS_BY_TYPE[type]
  const flatY = cuspEdge === 'bottom' ? 3 : 41
  const baseY = cuspEdge === 'bottom' ? 40 : 4
  const bump = Math.min((right - left) / (cusps * 2.4), 4.5)
  const outSign = cuspEdge === 'bottom' ? 1 : -1
  const cornerSign = cuspEdge === 'bottom' ? 1 : -1

  let d = `M ${left} ${flatY + cornerSign * CORNER_R} `
  d += `Q ${left} ${flatY} ${left + CORNER_R} ${flatY} `
  d += `L ${right - CORNER_R} ${flatY} `
  d += `Q ${right} ${flatY} ${right} ${flatY + cornerSign * CORNER_R} `
  d += `L ${right} ${baseY - outSign * bump * 0.6} `

  const segment = (right - left) / cusps
  for (let i = 0; i < cusps; i++) {
    const xStart = right - i * segment
    const xMid = xStart - segment / 2
    const xEnd = right - (i + 1) * segment
    d += `Q ${xMid} ${baseY + outSign * bump} ${xEnd} ${baseY - outSign * bump * 0.2} `
  }

  d += `L ${left} ${flatY + cornerSign * CORNER_R} Z`
  return d
}

/** Lobulos/cuspides decorativos que se asoman del borde oclusal/incisal (motivo "trebol"
 * de la vista oclusal del PDF de referencia) -- `<circle>`, nunca `<rect>`. */
export function cuspLobes(
  type: ToothVisualType,
  cuspEdge: 'top' | 'bottom',
): Array<{ cx: number; cy: number; r: number }> {
  const width = crownWidth(type)
  const left = CROWN_CENTER_X - width / 2 + 2
  const right = CROWN_CENTER_X + width / 2 - 2
  const cusps = CUSPS_BY_TYPE[type]
  const segment = (right - left) / cusps
  const r = Math.min(segment * 0.46, 5.2)
  const cy = cuspEdge === 'bottom' ? 41 : 3
  return Array.from({ length: cusps }, (_, i) => ({
    cx: left + segment * (i + 0.5),
    cy,
    r,
  }))
}

export interface RootShape {
  d: string
}

const ROOT_WIDTH_BY_TYPE: Record<ToothVisualType, number> = {
  anterior: 11,
  premolar: 15,
  molar: 34,
}

function rootPetal(cxBase: number, cxTip: number, halfBase: number, junctionY: number, tipY: number): string {
  const midY = (junctionY + tipY) / 2
  return (
    `M ${cxBase - halfBase} ${junctionY} ` +
    `Q ${cxBase - halfBase * 0.25} ${midY} ${cxTip} ${tipY} ` +
    `Q ${cxBase + halfBase * 0.25} ${midY} ${cxBase + halfBase} ${junctionY} Z`
  )
}

/**
 * Raices decorativas que se afinan hacia la punta. Una sola raiz en anteriores y
 * premolares; en molares, 2 (inferiores) o 3 (superiores, incluye una raiz palatina mas
 * corta al centro) que divergen desde la base -- aproximacion razonable, no busca ser una
 * replica anatomica exacta (ver plan: el periodontograma, fuera de este encargo, es el
 * lugar para el detalle radicular fino).
 *
 * `junctionY` es donde la raiz se une a la corona (base, ancha) y `tipY` hacia donde se
 * afina (punta); el signo de (tipY - junctionY) ya codifica la direccion correcta segun la
 * arcada (ver Tooth.tsx), asi que esta funcion no necesita saber si es superior o inferior.
 */
export function rootShapes(type: ToothVisualType, isUpperMolar: boolean, junctionY: number, tipY: number): RootShape[] {
  const totalWidth = ROOT_WIDTH_BY_TYPE[type]
  const span = tipY - junctionY

  if (type !== 'molar') {
    const halfBase = totalWidth / 2
    return [{ d: rootPetal(CROWN_CENTER_X, CROWN_CENTER_X, halfBase, junctionY, tipY) }]
  }

  const outerHalfBase = totalWidth / 2 / (isUpperMolar ? 2.3 : 1.7)
  const splay = totalWidth / 2 - outerHalfBase * 0.3
  const leftBase = CROWN_CENTER_X - totalWidth / 4
  const rightBase = CROWN_CENTER_X + totalWidth / 4
  const shapes = [
    { d: rootPetal(leftBase, CROWN_CENTER_X - splay, outerHalfBase, junctionY, tipY) },
    { d: rootPetal(rightBase, CROWN_CENTER_X + splay, outerHalfBase, junctionY, tipY) },
  ]
  if (isUpperMolar) {
    const centerTipY = junctionY + span * 0.72
    shapes.push({ d: rootPetal(CROWN_CENTER_X, CROWN_CENTER_X, outerHalfBase * 0.85, junctionY, centerTipY) })
  }
  return shapes
}
