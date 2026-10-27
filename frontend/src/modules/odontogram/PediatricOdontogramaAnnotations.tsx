import type { CatalogItemOut } from '../catalogs/types'
import type { PediatricToothAnnotationOut } from '../pediatricHistory/types'
import {
  anomalyAbbreviation,
  TOOTH_ANOMALY_ACQUIRED_ABSENCE,
  TOOTH_ANOMALY_CONGENITAL_ABSENCE,
} from '../pediatricHistory/types'
import styles from './PediatricOdontogramaAnnotations.module.css'
import { LOWER_PERMANENT_ROW, LOWER_TEMPORARY_ROW, UPPER_PERMANENT_ROW, UPPER_TEMPORARY_ROW } from './toothRules'

/**
 * Fase E (rediseno del expediente, docs/clinica): capa de anotaciones por
 * pieza del odontograma pediatrico (`PediatricToothAnnotation`, 8
 * abreviaturas + 2 especiales dibujadas como triangulo).
 *
 * DECISION DE DISENO (overlay): la opcion mas segura, pedida explicitamente
 * en el encargo, es NO modificar `Tooth.tsx`/`Arch.tsx` (ya probados y en uso
 * por Fases B/C y por `treatment`). Se evaluo superponer esta capa en pixeles
 * exactos encima del SVG real del <Odontograma>, pero se descarto por dos
 * razones concretas:
 *  1. El <Odontograma> administra su propio `viewMode` (permanente/
 *     temporal/mixta) como estado interno, sin exponerlo hacia afuera -- este
 *     componente no puede saber en todo momento cual arcada esta realmente
 *     visible para alinear pixeles contra ella.
 *  2. Arch.module.css usa flexbox con `overflow-x: auto` y `justify-content:
 *     center`: el ancho/posicion de cada pieza depende del viewport y de si
 *     hay scroll horizontal, lo que vuelve fragil cualquier calculo de
 *     posicion absoluta en px (se rompe con zoom, resize o tablet).
 *
 * En su lugar, este componente reutiliza el MISMO orden de filas/columnas
 * FDI que expone toothRules.ts (UPPER_TEMPORARY_ROW, UPPER_PERMANENT_ROW,
 * LOWER_PERMANENT_ROW, LOWER_TEMPORARY_ROW) para dibujar una franja propia,
 * siempre con las 4 arcadas visibles (independiente del viewMode elegido
 * arriba), inmediatamente debajo del <Odontograma> ya renderizado. Cada
 * celda corresponde por numero de pieza y por posicion relativa a la pieza
 * real de arriba -- el "overlay" es logico (misma correspondencia FDI
 * pieza-por-pieza) en vez de pixel-perfecto, lo que es mucho mas simple,
 * estable entre tamanos de pantalla, y no depende de medir el DOM interno
 * del odontograma.
 */

function ToothCell({
  tooth,
  annotations,
  catalogByCode,
}: {
  tooth: number
  annotations: PediatricToothAnnotationOut[]
  catalogByCode: Map<string, CatalogItemOut>
}) {
  const congenital = annotations.find((a) => a.anomaly_code === TOOTH_ANOMALY_CONGENITAL_ABSENCE)
  const acquired = annotations.find((a) => a.anomaly_code === TOOTH_ANOMALY_ACQUIRED_ABSENCE)
  const badgeAnnotations = annotations.filter(
    (a) =>
      a.anomaly_code !== TOOTH_ANOMALY_CONGENITAL_ABSENCE &&
      a.anomaly_code !== TOOTH_ANOMALY_ACQUIRED_ABSENCE,
  )

  return (
    <div className={styles.cell}>
      <span className={styles.cellNumber}>{tooth}</span>
      {congenital ? (
        <span
          className={`${styles.triangle} ${styles.triangleCongenital}`}
          role="img"
          aria-label={`Pieza ${tooth}: ausente congenito`}
          title="Ausente (congenito)"
        />
      ) : acquired ? (
        <span
          className={`${styles.triangle} ${styles.triangleAcquired}`}
          role="img"
          aria-label={`Pieza ${tooth}: ausente por extraccion o exfoliacion`}
          title="Ausente por extraccion o exfoliacion"
        />
      ) : badgeAnnotations.length > 0 ? (
        <span
          className={styles.badge}
          title={badgeAnnotations
            .map((a) => catalogByCode.get(a.anomaly_code)?.name ?? a.anomaly_code)
            .join(', ')}
        >
          {badgeAnnotations
            .map((a) => {
              const catalogItem = catalogByCode.get(a.anomaly_code)
              return catalogItem ? anomalyAbbreviation(catalogItem) : a.anomaly_code
            })
            .join(',')}
        </span>
      ) : (
        <span className={styles.badgeEmpty}>&middot;</span>
      )}
    </div>
  )
}

function AnnotationRow({
  teeth,
  annotationsByTooth,
  catalogByCode,
}: {
  teeth: number[]
  annotationsByTooth: Map<string, PediatricToothAnnotationOut[]>
  catalogByCode: Map<string, CatalogItemOut>
}) {
  return (
    <div className={styles.row}>
      {teeth.map((tooth) => (
        <ToothCell
          key={tooth}
          tooth={tooth}
          annotations={annotationsByTooth.get(String(tooth)) ?? []}
          catalogByCode={catalogByCode}
        />
      ))}
    </div>
  )
}

export function PediatricOdontogramaAnnotations({
  annotations,
  catalog,
}: {
  /** Anotaciones ACTIVAS (ya filtradas por is_active) de todas las
   * atenciones del paciente -- el overlay siempre muestra el estado vigente
   * por pieza, sin importar en que atencion se capturo cada una. */
  annotations: PediatricToothAnnotationOut[]
  catalog: CatalogItemOut[]
}) {
  const annotationsByTooth = new Map<string, PediatricToothAnnotationOut[]>()
  for (const annotation of annotations) {
    const list = annotationsByTooth.get(annotation.tooth_fdi) ?? []
    list.push(annotation)
    annotationsByTooth.set(annotation.tooth_fdi, list)
  }
  const catalogByCode = new Map(catalog.map((item) => [item.code, item]))

  return (
    <div className={styles.wrapper}>
      <p className={styles.title}>Anotaciones por pieza</p>
      <p className={styles.hint}>
        Misma posicion FDI que el odontograma de arriba (vista esquematica, ambas denticiones).
      </p>

      <p className={styles.rowLabel}>Temporales superiores</p>
      <AnnotationRow
        teeth={UPPER_TEMPORARY_ROW}
        annotationsByTooth={annotationsByTooth}
        catalogByCode={catalogByCode}
      />
      <p className={styles.rowLabel}>Permanentes superiores</p>
      <AnnotationRow
        teeth={UPPER_PERMANENT_ROW}
        annotationsByTooth={annotationsByTooth}
        catalogByCode={catalogByCode}
      />
      <div className={styles.midline} />
      <p className={styles.rowLabel}>Permanentes inferiores</p>
      <AnnotationRow
        teeth={LOWER_PERMANENT_ROW}
        annotationsByTooth={annotationsByTooth}
        catalogByCode={catalogByCode}
      />
      <p className={styles.rowLabel}>Temporales inferiores</p>
      <AnnotationRow
        teeth={LOWER_TEMPORARY_ROW}
        annotationsByTooth={annotationsByTooth}
        catalogByCode={catalogByCode}
      />

      <div className={styles.legend}>
        <span className={styles.legendItem}>
          <span
            className={`${styles.legendTriangle} ${styles.triangleCongenital}`}
          />
          Ausente (congenito)
        </span>
        <span className={styles.legendItem}>
          <span
            className={`${styles.legendTriangle} ${styles.triangleAcquired}`}
          />
          Ausente por extraccion o exfoliacion
        </span>
        <span className={styles.legendItem}>
          <span className={styles.badge}>Abr</span>
          Otras anomalias (ver abreviatura y detalle en la lista de abajo)
        </span>
      </div>
    </div>
  )
}
