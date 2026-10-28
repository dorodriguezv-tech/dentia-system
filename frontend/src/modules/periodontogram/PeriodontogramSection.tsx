import { useEffect, useRef, useState } from 'react'
import type { RefObject } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { LOWER_PERMANENT_ROW, UPPER_PERMANENT_ROW } from '../odontogram/toothRules'
import { AUTO_CORRECTION_REASON, latestActive, saveWithAutoCorrection } from '../patients/historyHelpers'
import { AnnulButton, DetailList, EditingBanner, MissingDataBadge } from '../patients/historyShared'
import styles from '../patients/PatientDetailPage.module.css'
import * as periodontogramApi from './api'
import localStyles from './PeriodontogramSection.module.css'
import {
  GINGIVAL_GRADE_LABELS,
  INDEX_SURFACES,
  INDEX_SURFACE_LABELS,
  LINGUAL_FACE_SITES,
  OCCLUSAL_MOVEMENTS,
  OCCLUSAL_MOVEMENT_LABELS,
  PLAQUE_GRADE_LABELS,
  PROBING_DEPTH_MM_MAX,
  PROBING_DEPTH_MM_MIN,
  PROBING_SITE_LABELS,
  RECESSION_MM_MAX,
  RECESSION_MM_MIN,
  VESTIBULAR_FACE_SITES,
  type IndexSurface,
  type IndexType,
  type OcclusalMovement,
  type PeriodontalProbingSiteCreateInput,
  type PeriodontalProbingSiteOut,
  type PeriodontalToothMeasurementOut,
  type ProbingSite,
} from './types'

/** Fase G (rediseno del expediente, docs/clinica -- ULTIMO slice del
 * proyecto): Periodontograma completo. Se renderiza DENTRO de
 * OdontologicalHistoryTab.tsx (Fase C), inmediatamente despues de
 * "Odontograma de diagnostico" -- reutiliza el MISMO `encounterId` ya
 * resuelto por el EncounterPickerField de esa seccion "ancla" (ningun picker
 * nuevo aqui, ver convencion #3 del encargo).
 *
 * Las 32 piezas FDI permanentes se muestran siempre en el MISMO orden que el
 * resto de la app (UPPER_PERMANENT_ROW + LOWER_PERMANENT_ROW de
 * toothRules.ts), concatenadas en una sola lista de columnas con scroll
 * horizontal -- no se reinventa el orden ni se separa en 2 tablas por
 * arcada.
 */

const ALL_TEETH: string[] = [...UPPER_PERMANENT_ROW, ...LOWER_PERMANENT_ROW].map(String)

/** Entrada activa mas reciente por clave (p.ej. "11|vestibular") -- a
 * diferencia de `latestActive` de historyHelpers.ts (una sola entrada
 * vigente para TODA la seccion), aqui cada celda de la grilla tiene su
 * propia entrada vigente independiente. El backend solo auto-anula
 * dentro del MISMO encounter (ver service.py), asi que pueden coexistir
 * entradas activas de la misma pieza+sitio en distintos encounters -- se
 * muestra siempre la mas reciente por fecha, sin importar en cual
 * encounter se capturo. */
function latestActiveByKey<T extends { is_active: boolean; created_at: string }>(
  items: T[] | undefined,
  keyFn: (item: T) => string,
): Map<string, T> {
  const map = new Map<string, T>()
  for (const item of items ?? []) {
    if (!item.is_active) continue
    const key = keyFn(item)
    const existing = map.get(key)
    if (!existing || new Date(item.created_at).getTime() > new Date(existing.created_at).getTime()) {
      map.set(key, item)
    }
  }
  return map
}

// --------------------------------------------------------------------------------
// 1. Sondeo periodontal -- 6 sitios por pieza (2 bloques de cara x 3 sitios).
//
// DECISION DE DISENO (captura de 192 celdas): a diferencia de las grillas de
// abajo (movilidad/furcacion, indices, oclusion), cada combinacion
// pieza+sitio aqui lleva 4 campos editables (profundidad, recesion,
// sangrado, supuracion) -- 192 x 4 = 768 campos simultaneos no es usable ni
// en monitor ni en tableta. Se usa el mismo patron de "panel inline" que
// FindingQuickMenu.tsx del odontograma (Fase B): el encabezado de cada
// columna pieza+sitio es un boton que abre un panel de edicion UNICO debajo
// de las tablas (no 192 paneles), con los 4 campos de esa celda. Las tablas
// solo MUESTRAN valores ya guardados (o "—"), nunca inputs inline.
// --------------------------------------------------------------------------------

function ProbingSiteEditPanel({
  tooth,
  site,
  current,
  pending,
  justSaved,
  encounterMissing,
  panelRef,
  onClose,
  onSubmit,
}: {
  tooth: string
  site: ProbingSite
  current: PeriodontalProbingSiteOut | undefined
  pending: boolean
  justSaved: boolean
  encounterMissing: boolean
  panelRef: RefObject<HTMLDivElement>
  onClose: () => void
  onSubmit: (data: {
    probing_depth_mm: number
    recession_mm: number
    bleeding_on_probing: boolean
    suppuration: boolean
  }) => void
}) {
  const [depth, setDepth] = useState(current ? String(current.probing_depth_mm) : '')
  const [recession, setRecession] = useState(current ? String(current.recession_mm) : '')
  const [bleeding, setBleeding] = useState(current?.bleeding_on_probing ?? false)
  const [suppuration, setSuppuration] = useState(current?.suppuration ?? false)

  useEffect(() => {
    // Precarga intencional del panel al cambiar de pieza+sitio seleccionado
    // (o al recibir su entrada activa) -- no es sincronizacion con un
    // sistema externo, mismo criterio que las demas precargas "editar" de
    // esta Historia Odontologica (ver historyHelpers.ts).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDepth(current ? String(current.probing_depth_mm) : '')
    setRecession(current ? String(current.recession_mm) : '')
    setBleeding(current?.bleeding_on_probing ?? false)
    setSuppuration(current?.suppuration ?? false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tooth, site, current?.id])

  const depthNum = depth.trim() === '' ? null : Number(depth)
  const recessionNum = recession.trim() === '' ? null : Number(recession)
  const valid =
    depthNum !== null &&
    !Number.isNaN(depthNum) &&
    depthNum >= PROBING_DEPTH_MM_MIN &&
    depthNum <= PROBING_DEPTH_MM_MAX &&
    recessionNum !== null &&
    !Number.isNaN(recessionNum) &&
    recessionNum >= RECESSION_MM_MIN &&
    recessionNum <= RECESSION_MM_MAX

  const nicPreview = valid ? (depthNum as number) + (recessionNum as number) : null
  const siteLabel = PROBING_SITE_LABELS[site]

  return (
    <div className={localStyles.editPanel} ref={panelRef}>
      <div className={localStyles.editPanelHeader}>
        <h4>
          Pieza {tooth} — {siteLabel}
        </h4>
        <button className={styles.linkButton} type="button" onClick={onClose}>
          Cerrar
        </button>
      </div>
      {current && (
        <p className={styles.helpText}>
          Ya guardado: profundidad {current.probing_depth_mm} mm, recesión {current.recession_mm} mm,
          NIC {current.clinical_attachment_level_mm ?? '—'} mm
          {current.bleeding_on_probing ? ', con sangrado al sondaje' : ''}
          {current.suppuration ? ', con supuración' : ''}. Edita y guarda para corregirlo.
        </p>
      )}
      <label className={styles.fieldRow}>
        <span>Profundidad de sondaje (mm)</span>
        <input
          type="number"
          step="1"
          min={PROBING_DEPTH_MM_MIN}
          max={PROBING_DEPTH_MM_MAX}
          aria-label={`Profundidad de sondaje pieza ${tooth} ${siteLabel}`}
          value={depth}
          onChange={(e) => setDepth(e.target.value)}
        />
      </label>
      <label className={styles.fieldRow}>
        <span>Recesión (mm)</span>
        <input
          type="number"
          step="1"
          min={RECESSION_MM_MIN}
          max={RECESSION_MM_MAX}
          aria-label={`Recesión pieza ${tooth} ${siteLabel}`}
          value={recession}
          onChange={(e) => setRecession(e.target.value)}
        />
      </label>
      <p className={styles.helpText}>NIC (calculado, no editable): {nicPreview ?? '—'} mm</p>
      <label className={styles.fieldRowCheckbox}>
        <input
          type="checkbox"
          checked={bleeding}
          onChange={(e) => setBleeding(e.target.checked)}
        />
        Sangrado al sondaje
      </label>
      <label className={styles.fieldRowCheckbox}>
        <input
          type="checkbox"
          checked={suppuration}
          onChange={(e) => setSuppuration(e.target.checked)}
        />
        Supuración
      </label>
      <div className={localStyles.editPanelActions}>
        <button
          className={styles.primaryButton}
          type="button"
          disabled={!valid || pending || encounterMissing}
          title={encounterMissing ? 'Selecciona o inicia una atencion' : undefined}
          onClick={() =>
            valid &&
            onSubmit({
              probing_depth_mm: depthNum as number,
              recession_mm: recessionNum as number,
              bleeding_on_probing: bleeding,
              suppuration,
            })
          }
        >
          {pending ? 'Guardando...' : 'Guardar sondeo'}
        </button>
        {justSaved && <span className={localStyles.savedConfirmation}>Guardado ✓</span>}
      </div>
    </div>
  )
}

const SUB_SITE_LABELS = ['Mesio', 'Centro', 'Disto']

function ProbingSitesSection({
  patientId,
  canWrite,
  encounterId,
}: {
  patientId: string
  canWrite: boolean
  encounterId: string
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['periodontogram-probing-sites', patientId],
    queryFn: () => periodontogramApi.listProbingSites(patientId),
  })
  const [selection, setSelection] = useState<{ tooth: string; site: ProbingSite } | null>(null)
  // Correccion: clave "pieza|sitio" del ultimo guardado exitoso, para mostrar
  // "Guardado ✓" sin cerrar el panel (antes se cerraba solo, dando la
  // sensacion de que no habia pasado nada). Se limpia al elegir otra
  // pieza/sitio.
  const [justSavedKey, setJustSavedKey] = useState<string | null>(null)
  const panelRef = useRef<HTMLDivElement | null>(null)

  const activeByKey = latestActiveByKey(listQuery.data, (item) => `${item.tooth_fdi}|${item.site}`)

  function selectSite(tooth: string, site: ProbingSite) {
    setJustSavedKey(null)
    setSelection({ tooth, site })
    // Corrección: el panel vive debajo de las 2 tablas -- en monitores
    // chicos o tableta puede quedar fuera de la vista al abrirse, dando la
    // sensación de que el clic no hizo nada.
    // jsdom (pruebas) no implementa scrollIntoView -- se protege la llamada
    // en vez de asumir que siempre existe en el entorno real del navegador.
    requestAnimationFrame(() => panelRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'center' }))
  }

  const createMutation = useMutation({
    mutationFn: (input: PeriodontalProbingSiteCreateInput) =>
      periodontogramApi.createProbingSite(patientId, input),
    onSuccess: (_result, variables) => {
      queryClient.invalidateQueries({ queryKey: ['periodontogram-probing-sites', patientId] })
      setJustSavedKey(`${variables.tooth_fdi}|${variables.site}`)
    },
  })

  function renderFaceTable(title: string, sites: ProbingSite[]) {
    return (
      <div className={localStyles.tableBlock}>
        <p className={styles.fieldsetLabel}>{title}</p>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Pieza</th>
                {ALL_TEETH.map((tooth) => (
                  <th key={tooth} colSpan={3} className={localStyles.dataCell}>
                    {tooth}
                  </th>
                ))}
              </tr>
              <tr>
                <th>Sitio</th>
                {ALL_TEETH.flatMap((tooth) =>
                  sites.map((site, idx) => {
                    const isSelected = selection?.tooth === tooth && selection.site === site
                    return (
                      <th key={`${tooth}-${site}-head`}>
                        {canWrite ? (
                          <button
                            type="button"
                            className={isSelected ? localStyles.siteButtonActive : localStyles.siteButton}
                            title={`Pieza ${tooth}: ${PROBING_SITE_LABELS[site]}`}
                            onClick={() => selectSite(tooth, site)}
                          >
                            {SUB_SITE_LABELS[idx]}
                          </button>
                        ) : (
                          <span title={`Pieza ${tooth}: ${PROBING_SITE_LABELS[site]}`}>
                            {SUB_SITE_LABELS[idx]}
                          </span>
                        )}
                      </th>
                    )
                  }),
                )}
              </tr>
            </thead>
            <tbody>
              {(
                [
                  {
                    label: 'Profundidad (mm)',
                    render: (entry: PeriodontalProbingSiteOut | undefined) =>
                      entry ? entry.probing_depth_mm : '—',
                  },
                  {
                    label: 'Recesión (mm)',
                    render: (entry: PeriodontalProbingSiteOut | undefined) =>
                      entry ? entry.recession_mm : '—',
                  },
                  {
                    label: 'NIC (calculado)',
                    render: (entry: PeriodontalProbingSiteOut | undefined) =>
                      entry?.clinical_attachment_level_mm ?? '—',
                  },
                  {
                    label: 'Sangrado',
                    render: (entry: PeriodontalProbingSiteOut | undefined) =>
                      entry?.bleeding_on_probing ? (
                        <span className={localStyles.boolYes}>Sí</span>
                      ) : (
                        <span className={localStyles.boolDash}>—</span>
                      ),
                  },
                  {
                    label: 'Supuración',
                    render: (entry: PeriodontalProbingSiteOut | undefined) =>
                      entry?.suppuration ? (
                        <span className={localStyles.boolYes}>Sí</span>
                      ) : (
                        <span className={localStyles.boolDash}>—</span>
                      ),
                  },
                ] as const
              ).map((row) => (
                <tr key={row.label}>
                  <th>{row.label}</th>
                  {ALL_TEETH.flatMap((tooth) =>
                    sites.map((site) => {
                      const entry = activeByKey.get(`${tooth}|${site}`)
                      const isSelected = selection?.tooth === tooth && selection.site === site
                      const cellClass = [
                        localStyles.dataCell,
                        canWrite ? localStyles.dataCellClickable : '',
                        isSelected ? localStyles.dataCellSelected : '',
                      ]
                        .filter(Boolean)
                        .join(' ')
                      return (
                        // El renglon entero de la columna (no solo el boton
                        // Mesio/Centro/Disto del encabezado) abre el panel
                        // de edicion -- correccion: antes solo el botoncito
                        // del encabezado era clicable, poco descubrible.
                        <td
                          key={`${tooth}-${site}-${row.label}`}
                          className={cellClass}
                          onClick={canWrite ? () => selectSite(tooth, site) : undefined}
                        >
                          {row.render(entry)}
                        </td>
                      )
                    }),
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  const selectedEntry = selection ? activeByKey.get(`${selection.tooth}|${selection.site}`) : undefined

  return (
    <div className={styles.fullWidth}>
      <h3>Sondeo periodontal</h3>
      <p className={styles.helpText}>
        Toca Mesio/Centro/Disto de una pieza para capturar o corregir su sondeo. El NIC se calcula
        solo (profundidad + recesión), nunca se edita directamente.
      </p>
      {renderFaceTable('Cara vestibular/bucal', VESTIBULAR_FACE_SITES)}
      {renderFaceTable('Cara lingual/palatina', LINGUAL_FACE_SITES)}

      {canWrite && selection && (
        <ProbingSiteEditPanel
          tooth={selection.tooth}
          site={selection.site}
          current={selectedEntry}
          pending={createMutation.isPending}
          justSaved={justSavedKey === `${selection.tooth}|${selection.site}`}
          encounterMissing={!encounterId}
          panelRef={panelRef}
          onClose={() => setSelection(null)}
          onSubmit={(data) =>
            createMutation.mutate({
              encounter_id: encounterId,
              tooth_fdi: selection.tooth,
              site: selection.site,
              ...data,
            })
          }
        />
      )}
    </div>
  )
}

// --------------------------------------------------------------------------------
// 2. Medicion por pieza -- movilidad (Miller) y furcacion. 2 filas x 32
// columnas, cada celda un <select> 0-3 (inline, sin panel: a diferencia del
// sondeo, aqui cada celda tiene un solo valor por campo).
// --------------------------------------------------------------------------------

function ToothMeasurementsSection({
  patientId,
  canWrite,
  encounterId,
}: {
  patientId: string
  canWrite: boolean
  encounterId: string
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['periodontogram-tooth-measurements', patientId],
    queryFn: () => periodontogramApi.listToothMeasurements(patientId),
  })

  const activeByTooth = latestActiveByKey(listQuery.data, (item) => item.tooth_fdi)

  const createMutation = useMutation({
    mutationFn: (variables: { tooth: string; mobility_grade: number | null; furcation_grade: number | null }) =>
      periodontogramApi.createToothMeasurement(patientId, {
        encounter_id: encounterId,
        tooth_fdi: variables.tooth,
        mobility_grade: variables.mobility_grade,
        furcation_grade: variables.furcation_grade,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['periodontogram-tooth-measurements', patientId] })
    },
  })

  function updateGrade(tooth: string, field: 'mobility_grade' | 'furcation_grade', value: string) {
    const current: PeriodontalToothMeasurementOut | undefined = activeByTooth.get(tooth)
    const grade = value === '' ? null : Number(value)
    createMutation.mutate({
      tooth,
      mobility_grade: field === 'mobility_grade' ? grade : current?.mobility_grade ?? null,
      furcation_grade: field === 'furcation_grade' ? grade : current?.furcation_grade ?? null,
    })
  }

  function gradeCell(tooth: string, field: 'mobility_grade' | 'furcation_grade', ariaLabel: string) {
    const current = activeByTooth.get(tooth)
    const value = current ? current[field] : null
    if (!canWrite) {
      return <span>{value ?? '—'}</span>
    }
    return (
      <select
        aria-label={ariaLabel}
        value={value === null || value === undefined ? '' : String(value)}
        disabled={!encounterId}
        onChange={(e) => updateGrade(tooth, field, e.target.value)}
      >
        <option value="">Sin registrar</option>
        <option value="0">0</option>
        <option value="1">1</option>
        <option value="2">2</option>
        <option value="3">3</option>
      </select>
    )
  }

  return (
    <div className={styles.fullWidth}>
      <h3>Movilidad (Miller) y furcación por pieza</h3>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Pieza</th>
              {ALL_TEETH.map((tooth) => (
                <th key={tooth} className={localStyles.dataCell}>
                  {tooth}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <th>Movilidad</th>
              {ALL_TEETH.map((tooth) => (
                <td key={tooth} className={localStyles.dataCell}>
                  {gradeCell(tooth, 'mobility_grade', `Movilidad pieza ${tooth}`)}
                </td>
              ))}
            </tr>
            <tr>
              <th>Furcación</th>
              {ALL_TEETH.map((tooth) => (
                <td key={tooth} className={localStyles.dataCell}>
                  {gradeCell(tooth, 'furcation_grade', `Furcación pieza ${tooth}`)}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}

// --------------------------------------------------------------------------------
// 3. Indices de placa dentobacteriana y gingival -- 2 superficies x 32
// columnas por indice, con leyenda de grados y resumen calculado.
// --------------------------------------------------------------------------------

function IndexGrid({
  patientId,
  canWrite,
  encounterId,
  indexType,
  title,
}: {
  patientId: string
  canWrite: boolean
  encounterId: string
  indexType: IndexType
  title: string
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['periodontogram-index-entries', patientId, indexType],
    queryFn: () => periodontogramApi.listIndexEntries(patientId, indexType),
  })
  const summaryQuery = useQuery({
    queryKey: ['periodontogram-indices-summary', patientId],
    queryFn: () => periodontogramApi.getIndicesSummary(patientId),
  })

  const activeByKey = latestActiveByKey(listQuery.data, (item) => `${item.tooth_fdi}|${item.surface}`)

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['periodontogram-index-entries', patientId, indexType] })
    queryClient.invalidateQueries({ queryKey: ['periodontogram-indices-summary', patientId] })
  }

  const createMutation = useMutation({
    mutationFn: (variables: { tooth: string; surface: IndexSurface; grade: number }) =>
      periodontogramApi.createIndexEntry(patientId, {
        encounter_id: encounterId,
        tooth_fdi: variables.tooth,
        index_type: indexType,
        surface: variables.surface,
        grade: variables.grade,
      }),
    onSuccess: invalidate,
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      periodontogramApi.annulIndexEntry(patientId, itemId, reason),
    onSuccess: invalidate,
  })

  function handleChange(tooth: string, surface: IndexSurface, value: string) {
    const current = activeByKey.get(`${tooth}|${surface}`)
    if (value === '') {
      // El grado es obligatorio en el backend (no admite null): "limpiar"
      // una celda ya capturada significa anular la entrada activa, no
      // recapturarla -- no se le pide motivo al usuario (correccion de
      // datos normal, mismo criterio que AUTO_CORRECTION_REASON).
      if (current) annulMutation.mutate({ itemId: current.id, reason: AUTO_CORRECTION_REASON })
      return
    }
    createMutation.mutate({ tooth, surface, grade: Number(value) })
  }

  const labels = indexType === 'placa' ? PLAQUE_GRADE_LABELS : GINGIVAL_GRADE_LABELS
  const summary = summaryQuery.data

  return (
    <div className={styles.fullWidth}>
      <h3>{title}</h3>

      {summary && indexType === 'placa' && (
        <dl className={localStyles.summaryBox}>
          <div className={styles.infoRow}>
            <dt>Número de caras totales</dt>
            <dd>{summary.placa.numero_caras_totales}</dd>
          </div>
          <div className={styles.infoRow}>
            <dt>Número de caras pigmentadas</dt>
            <dd>{summary.placa.numero_caras_pigmentadas}</dd>
          </div>
          <div className={styles.infoRow}>
            <dt>Índice calculado</dt>
            <dd>{summary.placa.indice_placa_dentobacteriana ?? 'Sin datos'}</dd>
          </div>
        </dl>
      )}
      {summary && indexType === 'gingival' && (
        <dl className={localStyles.summaryBox}>
          <div className={styles.infoRow}>
            <dt>Número de sitios totales</dt>
            <dd>{summary.gingival.numero_sitios_totales}</dd>
          </div>
          <div className={styles.infoRow}>
            <dt>Índice gingival total</dt>
            <dd>{summary.gingival.indice_gingival_total ?? 'Sin datos'}</dd>
          </div>
        </dl>
      )}

      <ul className={localStyles.legendList}>
        {[0, 1, 2, 3].map((grade) => (
          <li key={grade}>
            <strong>{grade}:</strong> {labels[grade]}
          </li>
        ))}
      </ul>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>Pieza</th>
              {ALL_TEETH.map((tooth) => (
                <th key={tooth} className={localStyles.dataCell}>
                  {tooth}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {INDEX_SURFACES.map((surface) => (
              <tr key={surface}>
                <th>{INDEX_SURFACE_LABELS[surface]}</th>
                {ALL_TEETH.map((tooth) => {
                  const entry = activeByKey.get(`${tooth}|${surface}`)
                  const value = entry ? String(entry.grade) : ''
                  return (
                    <td key={tooth} className={localStyles.dataCell}>
                      {canWrite ? (
                        <select
                          aria-label={`${title} ${INDEX_SURFACE_LABELS[surface]} pieza ${tooth}`}
                          value={value}
                          disabled={!encounterId}
                          onChange={(e) => handleChange(tooth, surface, e.target.value)}
                        >
                          <option value="">Sin especificar</option>
                          <option value="0">0</option>
                          <option value="1">1</option>
                          <option value="2">2</option>
                          <option value="3">3</option>
                        </select>
                      ) : (
                        <span>{value || '—'}</span>
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// --------------------------------------------------------------------------------
// 4. Tablas de oclusion -- 4 movimientos x 32 piezas, cada celda un
// checkbox. El backend es idempotente al marcar; para desmarcar se anula la
// entrada activa con un motivo automatico ("Desmarcado"), sin pedirselo al
// usuario.
// --------------------------------------------------------------------------------

function OcclusalContactsSection({
  patientId,
  canWrite,
  encounterId,
}: {
  patientId: string
  canWrite: boolean
  encounterId: string
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['periodontogram-occlusal-contacts', patientId],
    queryFn: () => periodontogramApi.listOcclusalContacts(patientId),
  })

  const activeByKey = latestActiveByKey(listQuery.data, (item) => `${item.tooth_fdi}|${item.movement}`)

  function invalidate() {
    queryClient.invalidateQueries({ queryKey: ['periodontogram-occlusal-contacts', patientId] })
  }

  const createMutation = useMutation({
    mutationFn: (variables: { tooth: string; movement: OcclusalMovement }) =>
      periodontogramApi.createOcclusalContact(patientId, {
        encounter_id: encounterId,
        tooth_fdi: variables.tooth,
        movement: variables.movement,
      }),
    onSuccess: invalidate,
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      periodontogramApi.annulOcclusalContact(patientId, itemId, reason),
    onSuccess: invalidate,
  })

  function toggle(tooth: string, movement: OcclusalMovement, checked: boolean) {
    if (checked) {
      createMutation.mutate({ tooth, movement })
      return
    }
    const current = activeByKey.get(`${tooth}|${movement}`)
    if (current) annulMutation.mutate({ itemId: current.id, reason: 'Desmarcado' })
  }

  return (
    <div className={styles.fullWidth}>
      <h3>Tablas de oclusión</h3>
      {OCCLUSAL_MOVEMENTS.map((movement) => (
        <div key={movement} className={localStyles.tableBlock}>
          <p className={styles.fieldsetLabel}>{OCCLUSAL_MOVEMENT_LABELS[movement]}</p>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Pieza</th>
                  {ALL_TEETH.map((tooth) => (
                    <th key={tooth} className={localStyles.dataCell}>
                      {tooth}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <th>Contacto</th>
                  {ALL_TEETH.map((tooth) => {
                    const checked = activeByKey.has(`${tooth}|${movement}`)
                    return (
                      <td key={tooth} className={localStyles.dataCell}>
                        {canWrite ? (
                          <input
                            type="checkbox"
                            className={localStyles.occlusalCheckbox}
                            aria-label={`${OCCLUSAL_MOVEMENT_LABELS[movement]} pieza ${tooth}`}
                            checked={checked}
                            disabled={!encounterId}
                            onChange={(e) => toggle(tooth, movement, e.target.checked)}
                          />
                        ) : checked ? (
                          <span className={localStyles.boolYes}>Sí</span>
                        ) : (
                          <span className={localStyles.boolDash}>—</span>
                        )}
                      </td>
                    )
                  })}
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  )
}

// --------------------------------------------------------------------------------
// 5. Observaciones del periodontograma -- un solo campo de texto por
// encounter: patron "Modificar singleton" ya existente en
// historyHelpers.ts/historyShared.tsx (formulario pre-llenado con la entrada
// activa mas reciente, auto-anula+recrea al guardar).
// --------------------------------------------------------------------------------

function ObservationsSection({
  patientId,
  canWrite,
  encounterId,
}: {
  patientId: string
  canWrite: boolean
  encounterId: string
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['periodontogram-observations', patientId],
    queryFn: () => periodontogramApi.listObservations(patientId),
  })
  const [observaciones, setObservaciones] = useState('')

  const current = latestActive(listQuery.data)

  useEffect(() => {
    // Correccion UX (ronda 2.2, mismo patron que el resto de la Historia
    // Odontologica): precarga intencional del formulario al cambiar la
    // entrada activa a editar -- no es sincronizacion con un sistema
    // externo, por eso se suprime la regla.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setObservaciones(current?.observaciones ?? '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        current,
        (itemId, reason) => periodontogramApi.annulObservation(patientId, itemId, reason),
        () =>
          periodontogramApi.createObservation(patientId, {
            encounter_id: encounterId,
            observaciones: observaciones || null,
          }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['periodontogram-observations', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      periodontogramApi.annulObservation(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['periodontogram-observations', patientId] })
    },
  })

  return (
    <div className={styles.fullWidth}>
      <h3>Observaciones del periodontograma</h3>
      {listQuery.data?.map((item) => (
        <div key={item.id} className={styles.contactItem}>
          <div>
            <p>
              {new Date(item.created_at).toLocaleString('es-MX')}
              {!item.is_active && ' (anulado)'}
            </p>
            <DetailList rows={item.observaciones ? [['Observaciones', item.observaciones]] : []} />
          </div>
          {canWrite && item.is_active && (
            <AnnulButton onAnnul={(reason) => annulMutation.mutate({ itemId: item.id, reason })} />
          )}
        </div>
      ))}
      {listQuery.data?.length === 0 && <p>Sin observaciones registradas.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <input
            type="text"
            placeholder="Observaciones (opcional)"
            value={observaciones}
            onChange={(e) => setObservaciones(e.target.value)}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Guardar observaciones'}
          </button>
        </form>
      )}
    </div>
  )
}

// --------------------------------------------------------------------------------
// PDF -- al final de la seccion (a diferencia del PDF de toda la Historia
// Odontologica, que va al inicio del tab).
// --------------------------------------------------------------------------------

function PeriodontogramPdfButton({ patientId }: { patientId: string }) {
  const [error, setError] = useState(false)
  const [generating, setGenerating] = useState(false)

  async function handleClick() {
    setError(false)
    setGenerating(true)
    const newTab = window.open('', '_blank')
    try {
      const url = await periodontogramApi.getPeriodontogramPdfBlobUrl(patientId)
      if (newTab) newTab.location.href = url
    } catch {
      newTab?.close()
      setError(true)
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className={styles.fullWidth}>
      <button
        className={styles.primaryButton}
        type="button"
        onClick={() => void handleClick()}
        disabled={generating}
      >
        {generating ? 'Generando PDF...' : 'Imprimir / Generar PDF'}
      </button>
      {error && <p className={styles.errorBox}>No se pudo generar el PDF.</p>}
    </div>
  )
}

// --------------------------------------------------------------------------------
// Seccion principal -- se monta dentro de OdontologicalHistoryTab.tsx,
// DESPUES de "Odontograma de diagnostico".
// --------------------------------------------------------------------------------

export function PeriodontogramSection({
  patientId,
  canWrite,
  encounterId,
}: {
  patientId: string
  canWrite: boolean
  encounterId: string
}) {
  // Consultas solo para el badge "Faltan datos" del <summary> -- mismas
  // query-keys que usan las subsecciones de abajo, TanStack Query las
  // comparte/deduplica mientras el <details> este montado (sin peticiones
  // de red extra en la practica).
  const probingQuery = useQuery({
    queryKey: ['periodontogram-probing-sites', patientId],
    queryFn: () => periodontogramApi.listProbingSites(patientId),
  })
  const measurementsQuery = useQuery({
    queryKey: ['periodontogram-tooth-measurements', patientId],
    queryFn: () => periodontogramApi.listToothMeasurements(patientId),
  })
  const occlusalQuery = useQuery({
    queryKey: ['periodontogram-occlusal-contacts', patientId],
    queryFn: () => periodontogramApi.listOcclusalContacts(patientId),
  })
  const observationsQuery = useQuery({
    queryKey: ['periodontogram-observations', patientId],
    queryFn: () => periodontogramApi.listObservations(patientId),
  })
  const placaQuery = useQuery({
    queryKey: ['periodontogram-index-entries', patientId, 'placa' as const],
    queryFn: () => periodontogramApi.listIndexEntries(patientId, 'placa'),
  })
  const gingivalQuery = useQuery({
    queryKey: ['periodontogram-index-entries', patientId, 'gingival' as const],
    queryFn: () => periodontogramApi.listIndexEntries(patientId, 'gingival'),
  })

  const hasActiveEntries =
    (probingQuery.data?.some((i) => i.is_active) ?? false) ||
    (measurementsQuery.data?.some((i) => i.is_active) ?? false) ||
    (occlusalQuery.data?.some((i) => i.is_active) ?? false) ||
    (observationsQuery.data?.some((i) => i.is_active) ?? false) ||
    (placaQuery.data?.some((i) => i.is_active) ?? false) ||
    (gingivalQuery.data?.some((i) => i.is_active) ?? false)

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Periodontograma completo
        <MissingDataBadge hasActiveEntries={hasActiveEntries} />
      </summary>

      <ProbingSitesSection patientId={patientId} canWrite={canWrite} encounterId={encounterId} />
      <ToothMeasurementsSection patientId={patientId} canWrite={canWrite} encounterId={encounterId} />
      <IndexGrid
        patientId={patientId}
        canWrite={canWrite}
        encounterId={encounterId}
        indexType="placa"
        title="Índice de placa dentobacteriana"
      />
      <IndexGrid
        patientId={patientId}
        canWrite={canWrite}
        encounterId={encounterId}
        indexType="gingival"
        title="Índice gingival"
      />
      <OcclusalContactsSection patientId={patientId} canWrite={canWrite} encounterId={encounterId} />
      <ObservationsSection patientId={patientId} canWrite={canWrite} encounterId={encounterId} />
      <PeriodontogramPdfButton patientId={patientId} />
    </details>
  )
}
