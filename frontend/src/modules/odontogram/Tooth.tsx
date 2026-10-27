import { FINDING_CATALOG } from './findingCatalog'
import styles from './Tooth.module.css'
import { crownOutlinePath, crownScaleX, cuspLobes, rootShapes } from './toothShapes'
import { isUpperTooth, toothLayout, toothVisualType } from './toothRules'
import type { Surface, ToothFindingOut } from './types'

const BOX = 44
const ROOT_HEIGHT = 22
const TOTAL_HEIGHT = BOX + ROOT_HEIGHT

interface ToothProps {
  toothFdi: number
  findings: ToothFindingOut[]
  small?: boolean
  selected: boolean
  onSurfaceClick: (toothFdi: number, surface: Surface | null) => void
}

/**
 * Silueta anatomica corona+raiz (Fase B). Mantiene exactamente las mismas 5 superficies
 * clicables de antes (mismas coordenadas, mismo orden en el DOM: top, bottom, left, right,
 * center -- ver Odontograma.test.tsx), solo cambia como se dibujan: encogidas/centradas
 * segun el tipo de pieza (anterior/premolar/molar, `toothVisualType`) dentro de un contorno
 * de corona con cuspides, mas una raiz decorativa (no clicable) que se afina hacia la
 * encia. La raiz queda del lado contrario a la linea donde las arcadas se tocan al morder
 * (CLAUDE.md no exige esto, es la referencia visual de docs/clinica): arriba de la corona
 * para piezas superiores, abajo para piezas inferiores.
 */
export function Tooth({ toothFdi, findings, small, selected, onSurfaceClick }: ToothProps) {
  const layout = toothLayout(toothFdi)
  const wholeTooth = findings.find((f) => f.surface === null)
  const bySurface = Object.fromEntries(
    findings.filter((f): f is ToothFindingOut & { surface: Surface } => f.surface !== null).map((f) => [f.surface, f]),
  )

  const width = small ? BOX * 0.72 : BOX
  const height = width * (TOTAL_HEIGHT / BOX)

  const upper = isUpperTooth(toothFdi)
  const visualType = toothVisualType(toothFdi)
  const isUpperMolar = upper && visualType === 'molar'
  const cuspEdge: 'top' | 'bottom' = upper ? 'bottom' : 'top'
  // Grupo de las 5 superficies: se desplaza 22 hacia abajo en piezas superiores (deja
  // espacio para la raiz arriba) y se queda donde siempre en piezas inferiores (la raiz se
  // agrega abajo, fuera de su espacio). Dentro de ese grupo, las coordenadas de los 5
  // <rect> no cambian -- solo se encogen/centran horizontalmente segun el tipo de pieza.
  const archTransform = upper ? `translate(0, ${ROOT_HEIGHT})` : undefined
  const scaleX = crownScaleX(visualType)
  const centerTransform = `translate(${22 - 22 * scaleX}, 0) scale(${scaleX}, 1)`

  const rootJunctionY = upper ? ROOT_HEIGHT : BOX
  const rootTipY = upper ? 0 : TOTAL_HEIGHT
  const roots = rootShapes(visualType, isUpperMolar, rootJunctionY, rootTipY)

  function regionProps(finding: ToothFindingOut | undefined) {
    const catalog = finding ? FINDING_CATALOG[finding.finding_code] : null
    return {
      fill: catalog ? catalog.color : 'var(--color-surface)',
      stroke: 'var(--color-border)',
      strokeDasharray: finding?.kind === 'PLANNED' ? ('3 2' as const) : undefined,
      vectorEffect: 'non-scaling-stroke' as const,
    }
  }

  return (
    <div
      className={small ? styles.toothSmall : styles.tooth}
      role="button"
      tabIndex={0}
      aria-label={`Pieza ${toothFdi}`}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') onSurfaceClick(toothFdi, null)
      }}
    >
      <svg
        className={selected ? styles.svgSelected : styles.svg}
        viewBox={`0 0 ${BOX} ${TOTAL_HEIGHT}`}
        width={width}
        height={height}
      >
        {roots.map((root, i) => (
          <path key={i} d={root.d} className={styles.rootShape} />
        ))}

        <g transform={archTransform}>
          <path d={crownOutlinePath(visualType, cuspEdge)} className={styles.crownOutline} />
          {cuspLobes(visualType, cuspEdge).map((lobe, i) => (
            <circle key={i} cx={lobe.cx} cy={lobe.cy} r={lobe.r} className={styles.crownOutline} />
          ))}

          <g transform={centerTransform}>
            {wholeTooth ? (
              <rect
                x={0}
                y={0}
                width={BOX}
                height={BOX}
                rx={6}
                {...regionProps(wholeTooth)}
                onClick={() => onSurfaceClick(toothFdi, null)}
              />
            ) : (
              <>
                <rect
                  x={11}
                  y={0}
                  width={22}
                  height={11}
                  {...regionProps(bySurface[layout.top])}
                  onClick={() => onSurfaceClick(toothFdi, layout.top)}
                />
                <rect
                  x={11}
                  y={33}
                  width={22}
                  height={11}
                  {...regionProps(bySurface[layout.bottom])}
                  onClick={() => onSurfaceClick(toothFdi, layout.bottom)}
                />
                <rect
                  x={0}
                  y={11}
                  width={11}
                  height={22}
                  {...regionProps(bySurface[layout.left])}
                  onClick={() => onSurfaceClick(toothFdi, layout.left)}
                />
                <rect
                  x={33}
                  y={11}
                  width={11}
                  height={22}
                  {...regionProps(bySurface[layout.right])}
                  onClick={() => onSurfaceClick(toothFdi, layout.right)}
                />
                <rect
                  x={11}
                  y={11}
                  width={22}
                  height={22}
                  {...regionProps(bySurface[layout.center])}
                  onClick={() => onSurfaceClick(toothFdi, layout.center)}
                />
              </>
            )}
          </g>

          {wholeTooth && FINDING_CATALOG[wholeTooth.finding_code].symbol && (
            <text x={BOX / 2} y={BOX / 2 + 4} textAnchor="middle" className={styles.symbol}>
              {FINDING_CATALOG[wholeTooth.finding_code].symbol}
            </text>
          )}
        </g>
      </svg>
      <span className={styles.label}>{toothFdi}</span>
    </div>
  )
}
