import { FINDING_CATALOG } from './findingCatalog'
import styles from './Tooth.module.css'
import { toothLayout } from './toothRules'
import type { Surface, ToothFindingOut } from './types'

const BOX = 44

interface ToothProps {
  toothFdi: number
  findings: ToothFindingOut[]
  small?: boolean
  selected: boolean
  onSurfaceClick: (toothFdi: number, surface: Surface | null) => void
}

export function Tooth({ toothFdi, findings, small, selected, onSurfaceClick }: ToothProps) {
  const layout = toothLayout(toothFdi)
  const wholeTooth = findings.find((f) => f.surface === null)
  const bySurface = Object.fromEntries(
    findings.filter((f): f is ToothFindingOut & { surface: Surface } => f.surface !== null).map((f) => [f.surface, f]),
  )

  const size = small ? BOX * 0.72 : BOX

  function regionProps(finding: ToothFindingOut | undefined) {
    const catalog = finding ? FINDING_CATALOG[finding.finding_code] : null
    return {
      fill: catalog ? catalog.color : 'var(--color-surface)',
      stroke: 'var(--color-border)',
      strokeDasharray: finding?.kind === 'PLANNED' ? '3 2' : undefined,
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
        viewBox={`0 0 ${BOX} ${BOX}`}
        width={size}
        height={size}
      >
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
        {wholeTooth && FINDING_CATALOG[wholeTooth.finding_code].symbol && (
          <text x={BOX / 2} y={BOX / 2 + 4} textAnchor="middle" className={styles.symbol}>
            {FINDING_CATALOG[wholeTooth.finding_code].symbol}
          </text>
        )}
      </svg>
      <span className={styles.label}>{toothFdi}</span>
    </div>
  )
}
