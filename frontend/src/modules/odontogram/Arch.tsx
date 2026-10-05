import { Tooth } from './Tooth'
import styles from './Arch.module.css'
import type { Surface, ToothFindingOut } from './types'

interface ArchProps {
  teeth: number[]
  findingsByTooth: Map<number, ToothFindingOut[]>
  small?: boolean
  selectedTooth: number | null
  onSurfaceClick: (toothFdi: number, surface: Surface | null) => void
}

export function Arch({ teeth, findingsByTooth, small, selectedTooth, onSurfaceClick }: ArchProps) {
  return (
    <div className={styles.row}>
      {teeth.map((toothFdi) => (
        <Tooth
          key={toothFdi}
          toothFdi={toothFdi}
          findings={findingsByTooth.get(toothFdi) ?? []}
          small={small}
          selected={selectedTooth === toothFdi}
          onSurfaceClick={onSurfaceClick}
        />
      ))}
    </div>
  )
}
