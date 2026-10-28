import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as endoApi from '../endodonticHistory/api'
import {
  ANTECEDENTES_KEYS,
  ANTECEDENTES_LABELS,
  CAMARA_KEYS,
  CAMARA_LABELS,
  CANAL_KEYS,
  CANAL_LABELS,
  CIRUGIA_KEYS,
  CIRUGIA_LABELS,
  CONDUCTO_KEYS,
  CONDUCTO_LABELS,
  DIAGNOSTICO_PERIAPICAL_LABELS,
  DIAGNOSTICO_PULPAR_LABELS,
  DOLOR_KEYS,
  DOLOR_LABELS,
  ENDODONTIC_TOOTH_CODES,
  ESTIMULO_KEYS,
  ESTIMULO_LABELS,
  EXAMEN_EXTRABUCAL_KEYS,
  EXAMEN_EXTRABUCAL_LABELS,
  EXAMEN_INTRABUCAL_KEYS,
  EXAMEN_INTRABUCAL_LABELS,
  PERCUSION_KEYS,
  PERCUSION_LABELS,
  PERIODONTO_KEYS,
  PERIODONTO_LABELS,
  TRATAMIENTO_KEYS,
  TRATAMIENTO_LABELS,
  type CanalMeasurementDetail,
  type DiagnosticoPeriapical,
  type DiagnosticoPulpar,
  type EndodonticDiagnosisTreatmentOut,
  type EndodonticInterrogationOut,
  type EndodonticPeriodontalTestOut,
  type EndodonticPulpSensitivityTestOut,
  type EndodonticRadiographicInterpretationOut,
  type EndodonticToothDiagnosisCodeOut,
  type EndodonticWorkingLengthOut,
  type MovilidadGrado,
  type MovilidadValue,
  type PalpacionValue,
} from '../endodonticHistory/types'
import { EncounterPickerField } from '../encounters/EncounterPicker'
import type { EncounterPicker } from '../encounters/useEncounterPicker'
import { LOWER_PERMANENT_ROW, UPPER_PERMANENT_ROW } from '../odontogram/toothRules'
import { latestActive, saveWithAutoCorrection } from './historyHelpers'
import { AnnulButton, DetailList, EditingBanner, MissingDataBadge } from './historyShared'
import styles from './PatientDetailPage.module.css'

/** Fase F (rediseno del expediente, docs/clinica): Historia Clinica de
 * Endodoncia -- mismo patron ya establecido en OdontologicalHistoryTab.tsx
 * (Fase C) y PediatricHistoryTab.tsx (Fase E): secciones <details> cerradas
 * por defecto (ronda de correcciones 2.1: sin excepcion, ni siquiera la
 * seccion ancla), badge "Faltan datos", vista "ya guardado" tipo <dl>, y
 * patron "editar" (ronda 2.2) en las secciones de una sola entrada vigente
 * (anular+recapturar por dentro, nunca borrado fisico -- regla 2 de
 * CLAUDE.md). La seccion ancla (unica con EncounterPickerField) es el
 * Odontograma de diagnostico/evolucion de 18 codigos. */

// --------------------------------------------------------------------------------
// Helper generico: checklist con "Otro/Otros" + texto condicional. Reutilizado
// por Interrogatorio (5 checklists) e Interpretacion radiografica (3
// checklists); Diagnostico y tratamiento usa checklists SIN "otro".
// --------------------------------------------------------------------------------

function ChecklistField({
  legend,
  keys,
  labels,
  values,
  onToggle,
  otherKey,
  otherDetail,
  onOtherDetailChange,
}: {
  legend: string
  keys: readonly string[]
  labels: Record<string, string>
  values: Record<string, boolean>
  onToggle: (key: string, checked: boolean) => void
  otherKey?: string
  otherDetail?: string
  onOtherDetailChange?: (value: string) => void
}) {
  return (
    <div>
      <p className={styles.fieldsetLabel}>{legend}</p>
      <div className={styles.checkboxGrid}>
        {keys.map((key) => (
          <label key={key} className={styles.checkboxItem}>
            <input
              type="checkbox"
              checked={values[key] ?? false}
              onChange={(e) => onToggle(key, e.target.checked)}
            />
            {labels[key]}
          </label>
        ))}
      </div>
      {otherKey && values[otherKey] && onOtherDetailChange && (
        <input
          type="text"
          placeholder="¿Cuál? (otro)"
          aria-label={`${legend}: detalle de otro`}
          value={otherDetail ?? ''}
          onChange={(e) => onOtherDetailChange(e.target.value)}
        />
      )}
    </div>
  )
}

function checklistDetailRow(
  legend: string,
  keys: readonly string[],
  labels: Record<string, string>,
  values: Record<string, boolean>,
  otherDetail?: string | null,
): [string, string] | null {
  const present = keys.filter((k) => values[k])
  if (present.length === 0) return null
  const names = present.map((k) => labels[k] ?? k)
  const detail = otherDetail ? ` (${otherDetail})` : ''
  return [legend, `${names.join(', ')}${detail}`]
}

// --------------------------------------------------------------------------------
// 1. Interrogatorio + examen intrabucal/extrabucal.
// --------------------------------------------------------------------------------

function InterrogationSection({
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
    queryKey: ['endo-history-interrogation', patientId],
    queryFn: () => endoApi.listInterrogations(patientId),
  })

  const [antecedentes, setAntecedentes] = useState<Record<string, boolean>>({})
  const [antecedentesOtroDetalle, setAntecedentesOtroDetalle] = useState('')
  const [dolor, setDolor] = useState<Record<string, boolean>>({})
  const [dolorOtroDetalle, setDolorOtroDetalle] = useState('')
  const [estimulo, setEstimulo] = useState<Record<string, boolean>>({})
  const [estimuloOtroDetalle, setEstimuloOtroDetalle] = useState('')
  const [examenIntrabucal, setExamenIntrabucal] = useState<Record<string, boolean>>({})
  const [examenIntrabucalOtroDetalle, setExamenIntrabucalOtroDetalle] = useState('')
  const [examenExtrabucal, setExamenExtrabucal] = useState<Record<string, boolean>>({})
  const [examenExtrabucalOtroDetalle, setExamenExtrabucalOtroDetalle] = useState('')

  // Correccion UX (ronda 2.2): entrada activa mas reciente -- se precarga el
  // formulario para "editarla" (anular+recapturar por dentro).
  const current = latestActive(listQuery.data)

  useEffect(() => {
    if (current) {
      // Correccion UX (ronda 2.2): precarga intencional del formulario al
      // cambiar la entrada activa a editar -- no es sincronizacion con un
      // sistema externo, por eso se suprime la regla.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAntecedentes(current.antecedentes)
      setAntecedentesOtroDetalle(current.antecedentes_otro_detalle ?? '')
      setDolor(current.dolor)
      setDolorOtroDetalle(current.dolor_otro_detalle ?? '')
      setEstimulo(current.estimulo)
      setEstimuloOtroDetalle(current.estimulo_otro_detalle ?? '')
      setExamenIntrabucal(current.examen_intrabucal)
      setExamenIntrabucalOtroDetalle(current.examen_intrabucal_otro_detalle ?? '')
      setExamenExtrabucal(current.examen_extrabucal)
      setExamenExtrabucalOtroDetalle(current.examen_extrabucal_otro_detalle ?? '')
    } else {
      setAntecedentes({})
      setAntecedentesOtroDetalle('')
      setDolor({})
      setDolorOtroDetalle('')
      setEstimulo({})
      setEstimuloOtroDetalle('')
      setExamenIntrabucal({})
      setExamenIntrabucalOtroDetalle('')
      setExamenExtrabucal({})
      setExamenExtrabucalOtroDetalle('')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        current,
        (itemId, reason) => endoApi.annulInterrogation(patientId, itemId, reason),
        () =>
          endoApi.createInterrogation(patientId, {
            encounter_id: encounterId,
            antecedentes,
            antecedentes_otro_detalle: antecedentesOtroDetalle || null,
            dolor,
            dolor_otro_detalle: dolorOtroDetalle || null,
            estimulo,
            estimulo_otro_detalle: estimuloOtroDetalle || null,
            examen_intrabucal: examenIntrabucal,
            examen_intrabucal_otro_detalle: examenIntrabucalOtroDetalle || null,
            examen_extrabucal: examenExtrabucal,
            examen_extrabucal_otro_detalle: examenExtrabucalOtroDetalle || null,
          }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['endo-history-interrogation', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      endoApi.annulInterrogation(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['endo-history-interrogation', patientId] })
    },
  })

  function detailRows(item: EndodonticInterrogationOut): [string, string][] {
    const rows: ([string, string] | null)[] = [
      checklistDetailRow(
        'Antecedentes',
        ANTECEDENTES_KEYS,
        ANTECEDENTES_LABELS,
        item.antecedentes,
        item.antecedentes_otro_detalle,
      ),
      checklistDetailRow('Dolor', DOLOR_KEYS, DOLOR_LABELS, item.dolor, item.dolor_otro_detalle),
      checklistDetailRow(
        'Estímulo',
        ESTIMULO_KEYS,
        ESTIMULO_LABELS,
        item.estimulo,
        item.estimulo_otro_detalle,
      ),
      checklistDetailRow(
        'Examen intrabucal',
        EXAMEN_INTRABUCAL_KEYS,
        EXAMEN_INTRABUCAL_LABELS,
        item.examen_intrabucal,
        item.examen_intrabucal_otro_detalle,
      ),
      checklistDetailRow(
        'Examen extrabucal',
        EXAMEN_EXTRABUCAL_KEYS,
        EXAMEN_EXTRABUCAL_LABELS,
        item.examen_extrabucal,
        item.examen_extrabucal_otro_detalle,
      ),
    ]
    return rows.filter((r): r is [string, string] => r !== null)
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Interrogatorio
        <MissingDataBadge hasActiveEntries={activeEntries.length > 0} />
      </summary>
      {listQuery.data?.map((item) => (
        <div key={item.id} className={styles.contactItem}>
          <div>
            <p>
              {new Date(item.created_at).toLocaleString('es-MX')}
              {!item.is_active && ' (anulado)'}
            </p>
            <DetailList rows={detailRows(item)} />
          </div>
          {canWrite && item.is_active && (
            <AnnulButton onAnnul={(reason) => annulMutation.mutate({ itemId: item.id, reason })} />
          )}
        </div>
      ))}
      {listQuery.data?.length === 0 && <p>Sin interrogatorio registrado.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <ChecklistField
            legend="Antecedentes"
            keys={ANTECEDENTES_KEYS}
            labels={ANTECEDENTES_LABELS}
            values={antecedentes}
            onToggle={(key, checked) => setAntecedentes((prev) => ({ ...prev, [key]: checked }))}
            otherKey="otros"
            otherDetail={antecedentesOtroDetalle}
            onOtherDetailChange={setAntecedentesOtroDetalle}
          />
          <ChecklistField
            legend="Dolor"
            keys={DOLOR_KEYS}
            labels={DOLOR_LABELS}
            values={dolor}
            onToggle={(key, checked) => setDolor((prev) => ({ ...prev, [key]: checked }))}
            otherKey="otro"
            otherDetail={dolorOtroDetalle}
            onOtherDetailChange={setDolorOtroDetalle}
          />
          <ChecklistField
            legend="Estímulo"
            keys={ESTIMULO_KEYS}
            labels={ESTIMULO_LABELS}
            values={estimulo}
            onToggle={(key, checked) => setEstimulo((prev) => ({ ...prev, [key]: checked }))}
            otherKey="otro"
            otherDetail={estimuloOtroDetalle}
            onOtherDetailChange={setEstimuloOtroDetalle}
          />
          <ChecklistField
            legend="Examen intrabucal"
            keys={EXAMEN_INTRABUCAL_KEYS}
            labels={EXAMEN_INTRABUCAL_LABELS}
            values={examenIntrabucal}
            onToggle={(key, checked) => setExamenIntrabucal((prev) => ({ ...prev, [key]: checked }))}
            otherKey="otro"
            otherDetail={examenIntrabucalOtroDetalle}
            onOtherDetailChange={setExamenIntrabucalOtroDetalle}
          />
          <ChecklistField
            legend="Examen extrabucal"
            keys={EXAMEN_EXTRABUCAL_KEYS}
            labels={EXAMEN_EXTRABUCAL_LABELS}
            values={examenExtrabucal}
            onToggle={(key, checked) => setExamenExtrabucal((prev) => ({ ...prev, [key]: checked }))}
            otherKey="otro"
            otherDetail={examenExtrabucalOtroDetalle}
            onOtherDetailChange={setExamenExtrabucalOtroDetalle}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Guardar interrogatorio'}
          </button>
        </form>
      )}
    </details>
  )
}

// --------------------------------------------------------------------------------
// 2. Pruebas de sensibilidad pulpar -- lista repetible por encuentro (varias
// pruebas, p.ej. una por pieza). Patron "editar" por fila (igual que
// FamilyHistorySection de la Historia Clinica General): "Modificar" precarga
// el formulario con ESA fila.
// --------------------------------------------------------------------------------

const PULP_BOOLEAN_FIELDS: { key: keyof typeof PULP_DEFAULTS; label: string }[] = [
  { key: 'frio', label: 'Frío' },
  { key: 'calor', label: 'Calor' },
  { key: 'fugaz', label: 'Fugaz' },
  { key: 'persistente', label: 'Persistente' },
  { key: 'localizado', label: 'Localizado' },
  { key: 'irradiado', label: 'Irradiado' },
  { key: 'decrece', label: 'Decrece' },
  { key: 'incrementa', label: 'Incrementa' },
]

const PULP_DEFAULTS = {
  frio: false,
  calor: false,
  fugaz: false,
  persistente: false,
  localizado: false,
  irradiado: false,
  decrece: false,
  incrementa: false,
  diente_testigo_od: '',
  prueba_cavidad: '',
  prueba_electrica_od: '',
}

function PulpSensitivityTestSection({
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
    queryKey: ['endo-history-pulp-sensitivity-test', patientId],
    queryFn: () => endoApi.listPulpSensitivityTests(patientId),
  })
  const [form, setForm] = useState(PULP_DEFAULTS)
  const [editingId, setEditingId] = useState<string | null>(null)

  function update<K extends keyof typeof PULP_DEFAULTS>(key: K, value: (typeof PULP_DEFAULTS)[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  function startEdit(item: EndodonticPulpSensitivityTestOut) {
    setEditingId(item.id)
    setForm({
      frio: item.frio,
      calor: item.calor,
      fugaz: item.fugaz,
      persistente: item.persistente,
      localizado: item.localizado,
      irradiado: item.irradiado,
      decrece: item.decrece,
      incrementa: item.incrementa,
      diente_testigo_od: item.diente_testigo_od ?? '',
      prueba_cavidad: item.prueba_cavidad ?? '',
      prueba_electrica_od: item.prueba_electrica_od ?? '',
    })
  }

  function cancelEdit() {
    setEditingId(null)
    setForm(PULP_DEFAULTS)
  }

  const editingEntry = editingId
    ? (listQuery.data ?? []).find((item) => item.id === editingId && item.is_active)
    : undefined

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        editingEntry,
        (itemId, reason) => endoApi.annulPulpSensitivityTest(patientId, itemId, reason),
        () =>
          endoApi.createPulpSensitivityTest(patientId, {
            encounter_id: encounterId,
            ...form,
            diente_testigo_od: form.diente_testigo_od || null,
            prueba_cavidad: form.prueba_cavidad || null,
            prueba_electrica_od: form.prueba_electrica_od || null,
          }),
      ),
    onSuccess: () => {
      setEditingId(null)
      setForm(PULP_DEFAULTS)
      queryClient.invalidateQueries({ queryKey: ['endo-history-pulp-sensitivity-test', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      endoApi.annulPulpSensitivityTest(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['endo-history-pulp-sensitivity-test', patientId] })
    },
  })

  function detailRows(item: EndodonticPulpSensitivityTestOut): [string, string][] {
    const rows: [string, string][] = []
    const present = PULP_BOOLEAN_FIELDS.filter(({ key }) => item[key as keyof typeof item]).map(
      ({ label }) => label,
    )
    if (present.length > 0) rows.push(['Hallazgos', present.join(', ')])
    if (item.diente_testigo_od) rows.push(['Diente testigo (OD)', item.diente_testigo_od])
    if (item.prueba_cavidad) rows.push(['Prueba de cavidad', item.prueba_cavidad])
    if (item.prueba_electrica_od) rows.push(['Prueba eléctrica (OD)', item.prueba_electrica_od])
    return rows
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Pruebas de sensibilidad pulpar
        <MissingDataBadge hasActiveEntries={activeEntries.length > 0} />
      </summary>
      {listQuery.data?.map((item) => (
        <div key={item.id} className={styles.contactItem}>
          <div>
            <p>
              {new Date(item.created_at).toLocaleString('es-MX')}
              {!item.is_active && ' (anulado)'}
            </p>
            <DetailList rows={detailRows(item)} />
          </div>
          {canWrite && item.is_active && (
            <span>
              <button className={styles.linkButton} type="button" onClick={() => startEdit(item)}>
                Modificar
              </button>{' '}
              <AnnulButton onAnnul={(reason) => annulMutation.mutate({ itemId: item.id, reason })} />
            </span>
          )}
        </div>
      ))}
      {listQuery.data?.length === 0 && <p>Sin pruebas de sensibilidad pulpar registradas.</p>}

      {canWrite && editingEntry && <EditingBanner createdAt={editingEntry.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <div className={styles.checkboxGrid}>
            {PULP_BOOLEAN_FIELDS.map(({ key, label }) => (
              <label key={key} className={styles.checkboxItem}>
                <input
                  type="checkbox"
                  checked={form[key] as boolean}
                  onChange={(e) => update(key, e.target.checked as (typeof form)[typeof key])}
                />
                {label}
              </label>
            ))}
          </div>
          <input
            type="text"
            placeholder="Diente testigo (OD)"
            value={form.diente_testigo_od}
            onChange={(e) => update('diente_testigo_od', e.target.value)}
          />
          <input
            type="text"
            placeholder="Prueba de cavidad"
            value={form.prueba_cavidad}
            onChange={(e) => update('prueba_cavidad', e.target.value)}
          />
          <input
            type="text"
            placeholder="Prueba eléctrica (OD)"
            value={form.prueba_electrica_od}
            onChange={(e) => update('prueba_electrica_od', e.target.value)}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {editingEntry ? 'Guardar cambios' : 'Agregar prueba'}
          </button>
          {editingId && (
            <button className={styles.linkButton} type="button" onClick={cancelEdit}>
              Cancelar edición
            </button>
          )}
        </form>
      )}
    </details>
  )
}

// --------------------------------------------------------------------------------
// 3. Pruebas periodontales -- 2 columnas (horizontal/vertical).
// --------------------------------------------------------------------------------

function MovilidadFields({
  legend,
  movilidad,
  grado,
  onMovilidadChange,
  onGradoChange,
}: {
  legend: string
  movilidad: MovilidadValue | ''
  grado: MovilidadGrado | ''
  onMovilidadChange: (value: MovilidadValue | '') => void
  onGradoChange: (value: MovilidadGrado | '') => void
}) {
  return (
    <>
      <select
        aria-label={legend}
        value={movilidad}
        onChange={(e) => onMovilidadChange(e.target.value as MovilidadValue | '')}
      >
        <option value="">{legend}: sin especificar</option>
        <option value="positiva">Positiva</option>
        <option value="negativa">Negativa</option>
      </select>
      {movilidad === 'positiva' && (
        <select
          aria-label={`${legend}: grado`}
          value={grado}
          onChange={(e) => onGradoChange(e.target.value as MovilidadGrado | '')}
        >
          <option value="">Grado: sin especificar</option>
          {(['I', 'II', 'III'] as MovilidadGrado[]).map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </select>
      )}
    </>
  )
}

function PeriodontalTestSection({
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
    queryKey: ['endo-history-periodontal-test', patientId],
    queryFn: () => endoApi.listPeriodontalTests(patientId),
  })

  const [percusionHorizontal, setPercusionHorizontal] = useState<Record<string, boolean>>({})
  const [movilidadHorizontal, setMovilidadHorizontal] = useState<MovilidadValue | ''>('')
  const [movilidadHorizontalGrado, setMovilidadHorizontalGrado] = useState<MovilidadGrado | ''>('')
  const [percusionVertical, setPercusionVertical] = useState<Record<string, boolean>>({})
  const [movilidadVertical, setMovilidadVertical] = useState<MovilidadValue | ''>('')
  const [movilidadVerticalGrado, setMovilidadVerticalGrado] = useState<MovilidadGrado | ''>('')
  const [palpacion, setPalpacion] = useState<PalpacionValue | ''>('')

  const current = latestActive(listQuery.data)

  useEffect(() => {
    if (current) {
      // Correccion UX (ronda 2.2): precarga intencional del formulario al
      // cambiar la entrada activa a editar -- no es sincronizacion con un
      // sistema externo, por eso se suprime la regla.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPercusionHorizontal(current.percusion_horizontal)
      setMovilidadHorizontal(current.movilidad_horizontal ?? '')
      setMovilidadHorizontalGrado(current.movilidad_horizontal_grado ?? '')
      setPercusionVertical(current.percusion_vertical)
      setMovilidadVertical(current.movilidad_vertical ?? '')
      setMovilidadVerticalGrado(current.movilidad_vertical_grado ?? '')
      setPalpacion(current.palpacion ?? '')
    } else {
      setPercusionHorizontal({})
      setMovilidadHorizontal('')
      setMovilidadHorizontalGrado('')
      setPercusionVertical({})
      setMovilidadVertical('')
      setMovilidadVerticalGrado('')
      setPalpacion('')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        current,
        (itemId, reason) => endoApi.annulPeriodontalTest(patientId, itemId, reason),
        () =>
          endoApi.createPeriodontalTest(patientId, {
            encounter_id: encounterId,
            percusion_horizontal: percusionHorizontal,
            movilidad_horizontal: movilidadHorizontal || null,
            movilidad_horizontal_grado: movilidadHorizontal === 'positiva' ? movilidadHorizontalGrado || null : null,
            percusion_vertical: percusionVertical,
            movilidad_vertical: movilidadVertical || null,
            movilidad_vertical_grado: movilidadVertical === 'positiva' ? movilidadVerticalGrado || null : null,
            palpacion: palpacion || null,
          }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['endo-history-periodontal-test', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      endoApi.annulPeriodontalTest(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['endo-history-periodontal-test', patientId] })
    },
  })

  function detailRows(item: EndodonticPeriodontalTestOut): [string, string][] {
    const rows: ([string, string] | null)[] = [
      checklistDetailRow('Percusión horizontal', PERCUSION_KEYS, PERCUSION_LABELS, item.percusion_horizontal),
      item.movilidad_horizontal
        ? [
            'Movilidad horizontal',
            `${item.movilidad_horizontal}${item.movilidad_horizontal_grado ? ` (grado ${item.movilidad_horizontal_grado})` : ''}`,
          ]
        : null,
      checklistDetailRow('Percusión vertical', PERCUSION_KEYS, PERCUSION_LABELS, item.percusion_vertical),
      item.movilidad_vertical
        ? [
            'Movilidad vertical',
            `${item.movilidad_vertical}${item.movilidad_vertical_grado ? ` (grado ${item.movilidad_vertical_grado})` : ''}`,
          ]
        : null,
      item.palpacion ? ['Palpación', item.palpacion] : null,
    ]
    return rows.filter((r): r is [string, string] => r !== null)
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Pruebas periodontales
        <MissingDataBadge hasActiveEntries={activeEntries.length > 0} />
      </summary>
      {listQuery.data?.map((item) => (
        <div key={item.id} className={styles.contactItem}>
          <div>
            <p>
              {new Date(item.created_at).toLocaleString('es-MX')}
              {!item.is_active && ' (anulado)'}
            </p>
            <DetailList rows={detailRows(item)} />
          </div>
          {canWrite && item.is_active && (
            <AnnulButton onAnnul={(reason) => annulMutation.mutate({ itemId: item.id, reason })} />
          )}
        </div>
      ))}
      {listQuery.data?.length === 0 && <p>Sin pruebas periodontales registradas.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem' }}>
            <div style={{ flex: '1 1 260px' }}>
              <p className={styles.fieldsetLabel}>Horizontal</p>
              <ChecklistField
                legend="Percusión horizontal"
                keys={PERCUSION_KEYS}
                labels={PERCUSION_LABELS}
                values={percusionHorizontal}
                onToggle={(key, checked) =>
                  setPercusionHorizontal((prev) => ({ ...prev, [key]: checked }))
                }
              />
              <MovilidadFields
                legend="Movilidad horizontal"
                movilidad={movilidadHorizontal}
                grado={movilidadHorizontalGrado}
                onMovilidadChange={setMovilidadHorizontal}
                onGradoChange={setMovilidadHorizontalGrado}
              />
            </div>
            <div style={{ flex: '1 1 260px' }}>
              <p className={styles.fieldsetLabel}>Vertical</p>
              <ChecklistField
                legend="Percusión vertical"
                keys={PERCUSION_KEYS}
                labels={PERCUSION_LABELS}
                values={percusionVertical}
                onToggle={(key, checked) =>
                  setPercusionVertical((prev) => ({ ...prev, [key]: checked }))
                }
              />
              <MovilidadFields
                legend="Movilidad vertical"
                movilidad={movilidadVertical}
                grado={movilidadVerticalGrado}
                onMovilidadChange={setMovilidadVertical}
                onGradoChange={setMovilidadVerticalGrado}
              />
            </div>
          </div>
          <select
            aria-label="Palpación"
            value={palpacion}
            onChange={(e) => setPalpacion(e.target.value as PalpacionValue | '')}
          >
            <option value="">Palpación: sin especificar</option>
            <option value="positiva">Positiva</option>
            <option value="negativa">Negativa</option>
          </select>
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Guardar pruebas periodontales'}
          </button>
        </form>
      )}
    </details>
  )
}

// --------------------------------------------------------------------------------
// 4. Interpretacion radiografica -- 3 columnas (camara/conducto/periodonto).
// --------------------------------------------------------------------------------

function RadiographicInterpretationSection({
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
    queryKey: ['endo-history-radiographic-interpretation', patientId],
    queryFn: () => endoApi.listRadiographicInterpretations(patientId),
  })

  const [camara, setCamara] = useState<Record<string, boolean>>({})
  const [camaraOtroDetalle, setCamaraOtroDetalle] = useState('')
  const [conducto, setConducto] = useState<Record<string, boolean>>({})
  const [conductoOtroDetalle, setConductoOtroDetalle] = useState('')
  const [periodonto, setPeriodonto] = useState<Record<string, boolean>>({})
  const [periodontoOtroDetalle, setPeriodontoOtroDetalle] = useState('')

  const current = latestActive(listQuery.data)

  useEffect(() => {
    if (current) {
      // Correccion UX (ronda 2.2): precarga intencional del formulario al
      // cambiar la entrada activa a editar -- no es sincronizacion con un
      // sistema externo, por eso se suprime la regla.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCamara(current.camara)
      setCamaraOtroDetalle(current.camara_otro_detalle ?? '')
      setConducto(current.conducto)
      setConductoOtroDetalle(current.conducto_otro_detalle ?? '')
      setPeriodonto(current.periodonto)
      setPeriodontoOtroDetalle(current.periodonto_otro_detalle ?? '')
    } else {
      setCamara({})
      setCamaraOtroDetalle('')
      setConducto({})
      setConductoOtroDetalle('')
      setPeriodonto({})
      setPeriodontoOtroDetalle('')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        current,
        (itemId, reason) => endoApi.annulRadiographicInterpretation(patientId, itemId, reason),
        () =>
          endoApi.createRadiographicInterpretation(patientId, {
            encounter_id: encounterId,
            camara,
            camara_otro_detalle: camaraOtroDetalle || null,
            conducto,
            conducto_otro_detalle: conductoOtroDetalle || null,
            periodonto,
            periodonto_otro_detalle: periodontoOtroDetalle || null,
          }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['endo-history-radiographic-interpretation', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      endoApi.annulRadiographicInterpretation(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['endo-history-radiographic-interpretation', patientId] })
    },
  })

  function detailRows(item: EndodonticRadiographicInterpretationOut): [string, string][] {
    const rows: ([string, string] | null)[] = [
      checklistDetailRow('Cámara', CAMARA_KEYS, CAMARA_LABELS, item.camara, item.camara_otro_detalle),
      checklistDetailRow('Conducto', CONDUCTO_KEYS, CONDUCTO_LABELS, item.conducto, item.conducto_otro_detalle),
      checklistDetailRow(
        'Periodonto',
        PERIODONTO_KEYS,
        PERIODONTO_LABELS,
        item.periodonto,
        item.periodonto_otro_detalle,
      ),
    ]
    return rows.filter((r): r is [string, string] => r !== null)
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Interpretación radiográfica
        <MissingDataBadge hasActiveEntries={activeEntries.length > 0} />
      </summary>
      {listQuery.data?.map((item) => (
        <div key={item.id} className={styles.contactItem}>
          <div>
            <p>
              {new Date(item.created_at).toLocaleString('es-MX')}
              {!item.is_active && ' (anulado)'}
            </p>
            <DetailList rows={detailRows(item)} />
          </div>
          {canWrite && item.is_active && (
            <AnnulButton onAnnul={(reason) => annulMutation.mutate({ itemId: item.id, reason })} />
          )}
        </div>
      ))}
      {listQuery.data?.length === 0 && <p>Sin interpretación radiográfica registrada.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem' }}>
            <div style={{ flex: '1 1 220px' }}>
              <ChecklistField
                legend="Cámara"
                keys={CAMARA_KEYS}
                labels={CAMARA_LABELS}
                values={camara}
                onToggle={(key, checked) => setCamara((prev) => ({ ...prev, [key]: checked }))}
                otherKey="otro"
                otherDetail={camaraOtroDetalle}
                onOtherDetailChange={setCamaraOtroDetalle}
              />
            </div>
            <div style={{ flex: '1 1 220px' }}>
              <ChecklistField
                legend="Conducto"
                keys={CONDUCTO_KEYS}
                labels={CONDUCTO_LABELS}
                values={conducto}
                onToggle={(key, checked) => setConducto((prev) => ({ ...prev, [key]: checked }))}
                otherKey="otro"
                otherDetail={conductoOtroDetalle}
                onOtherDetailChange={setConductoOtroDetalle}
              />
            </div>
            <div style={{ flex: '1 1 220px' }}>
              <ChecklistField
                legend="Periodonto"
                keys={PERIODONTO_KEYS}
                labels={PERIODONTO_LABELS}
                values={periodonto}
                onToggle={(key, checked) => setPeriodonto((prev) => ({ ...prev, [key]: checked }))}
                otherKey="otro"
                otherDetail={periodontoOtroDetalle}
                onOtherDetailChange={setPeriodontoOtroDetalle}
              />
            </div>
          </div>
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Guardar interpretación radiográfica'}
          </button>
        </form>
      )}
    </details>
  )
}

// --------------------------------------------------------------------------------
// 5. Diagnostico y tratamiento -- diagnosticos de seleccion UNICA (radio),
// tratamiento/cirugia multi-select (checklist, sin "otro").
// --------------------------------------------------------------------------------

function DiagnosisTreatmentSection({
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
    queryKey: ['endo-history-diagnosis-treatment', patientId],
    queryFn: () => endoApi.listDiagnosisTreatments(patientId),
  })

  const [diagnosticoPulpar, setDiagnosticoPulpar] = useState<DiagnosticoPulpar | ''>('')
  const [diagnosticoPeriapical, setDiagnosticoPeriapical] = useState<DiagnosticoPeriapical | ''>('')
  const [tratamiento, setTratamiento] = useState<Record<string, boolean>>({})
  const [cirugia, setCirugia] = useState<Record<string, boolean>>({})

  const current = latestActive(listQuery.data)

  useEffect(() => {
    if (current) {
      // Correccion UX (ronda 2.2): precarga intencional del formulario al
      // cambiar la entrada activa a editar -- no es sincronizacion con un
      // sistema externo, por eso se suprime la regla.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDiagnosticoPulpar(current.diagnostico_pulpar ?? '')
      setDiagnosticoPeriapical(current.diagnostico_periapical ?? '')
      setTratamiento(current.tratamiento)
      setCirugia(current.cirugia)
    } else {
      setDiagnosticoPulpar('')
      setDiagnosticoPeriapical('')
      setTratamiento({})
      setCirugia({})
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        current,
        (itemId, reason) => endoApi.annulDiagnosisTreatment(patientId, itemId, reason),
        () =>
          endoApi.createDiagnosisTreatment(patientId, {
            encounter_id: encounterId,
            diagnostico_pulpar: diagnosticoPulpar || null,
            diagnostico_periapical: diagnosticoPeriapical || null,
            tratamiento,
            cirugia,
          }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['endo-history-diagnosis-treatment', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      endoApi.annulDiagnosisTreatment(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['endo-history-diagnosis-treatment', patientId] })
    },
  })

  function detailRows(item: EndodonticDiagnosisTreatmentOut): [string, string][] {
    const rows: ([string, string] | null)[] = [
      item.diagnostico_pulpar
        ? ['Diagnóstico pulpar', DIAGNOSTICO_PULPAR_LABELS[item.diagnostico_pulpar]]
        : null,
      item.diagnostico_periapical
        ? ['Diagnóstico periapical', DIAGNOSTICO_PERIAPICAL_LABELS[item.diagnostico_periapical]]
        : null,
      checklistDetailRow('Tratamiento', TRATAMIENTO_KEYS, TRATAMIENTO_LABELS, item.tratamiento),
      checklistDetailRow('Cirugía', CIRUGIA_KEYS, CIRUGIA_LABELS, item.cirugia),
    ]
    return rows.filter((r): r is [string, string] => r !== null)
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Diagnóstico y tratamiento
        <MissingDataBadge hasActiveEntries={activeEntries.length > 0} />
      </summary>
      {listQuery.data?.map((item) => (
        <div key={item.id} className={styles.contactItem}>
          <div>
            <p>
              {new Date(item.created_at).toLocaleString('es-MX')}
              {!item.is_active && ' (anulado)'}
            </p>
            <DetailList rows={detailRows(item)} />
          </div>
          {canWrite && item.is_active && (
            <AnnulButton onAnnul={(reason) => annulMutation.mutate({ itemId: item.id, reason })} />
          )}
        </div>
      ))}
      {listQuery.data?.length === 0 && <p>Sin diagnóstico y tratamiento registrados.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <p className={styles.fieldsetLabel}>Diagnóstico pulpar</p>
          <div className={styles.checkboxGrid}>
            {(Object.entries(DIAGNOSTICO_PULPAR_LABELS) as [DiagnosticoPulpar, string][]).map(
              ([code, label]) => (
                <label key={code} className={styles.checkboxItem}>
                  <input
                    type="radio"
                    name="diagnostico_pulpar"
                    checked={diagnosticoPulpar === code}
                    onChange={() => setDiagnosticoPulpar(code)}
                  />
                  {label}
                </label>
              ),
            )}
          </div>
          <p className={styles.fieldsetLabel}>Diagnóstico periapical</p>
          <div className={styles.checkboxGrid}>
            {(Object.entries(DIAGNOSTICO_PERIAPICAL_LABELS) as [DiagnosticoPeriapical, string][]).map(
              ([code, label]) => (
                <label key={code} className={styles.checkboxItem}>
                  <input
                    type="radio"
                    name="diagnostico_periapical"
                    checked={diagnosticoPeriapical === code}
                    onChange={() => setDiagnosticoPeriapical(code)}
                  />
                  {label}
                </label>
              ),
            )}
          </div>
          <ChecklistField
            legend="Tratamiento"
            keys={TRATAMIENTO_KEYS}
            labels={TRATAMIENTO_LABELS}
            values={tratamiento}
            onToggle={(key, checked) => setTratamiento((prev) => ({ ...prev, [key]: checked }))}
          />
          <ChecklistField
            legend="Cirugía"
            keys={CIRUGIA_KEYS}
            labels={CIRUGIA_LABELS}
            values={cirugia}
            onToggle={(key, checked) => setCirugia((prev) => ({ ...prev, [key]: checked }))}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Guardar diagnóstico y tratamiento'}
          </button>
        </form>
      )}
    </details>
  )
}

// --------------------------------------------------------------------------------
// 6. Odontograma de diagnostico/evolucion -- seccion "ancla": es la UNICA
// seccion de esta pestana que renderiza el EncounterPickerField, por eso
// empieza ABIERTA por defecto (correccion posterior a la ronda 2.1: cerrarla
// como a las demas ocultaba el unico control para seleccionar/iniciar una
// atencion, deshabilitando en silencio el resto de la pestana). 18 codigos
// por pieza (0-17), solo piezas permanentes.
// --------------------------------------------------------------------------------

function ToothCodeGrid({
  patientId,
  canWrite,
  encounterId,
  kind,
  entries,
  onSaved,
}: {
  patientId: string
  canWrite: boolean
  encounterId: string
  kind: 'diagnostico' | 'evolucion'
  entries: EndodonticToothDiagnosisCodeOut[]
  onSaved: () => void
}) {
  const latestByTooth = new Map<string, EndodonticToothDiagnosisCodeOut>()
  for (const entry of entries.filter((e) => e.is_active)) {
    const existing = latestByTooth.get(entry.tooth_fdi)
    if (!existing || new Date(entry.created_at) > new Date(existing.created_at)) {
      latestByTooth.set(entry.tooth_fdi, entry)
    }
  }

  const saveMutation = useMutation({
    mutationFn: (vars: { tooth: string; code: number }) =>
      endoApi.createToothDiagnosisCode(patientId, {
        encounter_id: encounterId,
        tooth_fdi: vars.tooth,
        kind,
        code: vars.code,
      }),
    onSuccess: onSaved,
  })

  function renderRow(teeth: number[]) {
    return (
      <div className={styles.checkboxGrid}>
        {teeth.map((tooth) => {
          const current = latestByTooth.get(String(tooth))
          return (
            <label key={tooth} className={styles.fieldRow}>
              <span>{tooth}</span>
              <select
                aria-label={`Odontograma de ${kind} pieza ${tooth}`}
                value={current ? String(current.code) : ''}
                disabled={!canWrite || !encounterId}
                onChange={(e) => {
                  const code = Number(e.target.value)
                  if (!Number.isNaN(code)) saveMutation.mutate({ tooth: String(tooth), code })
                }}
              >
                <option value="">Sin registrar</option>
                {ENDODONTIC_TOOTH_CODES.map(([code, label]) => (
                  <option key={code} value={code}>
                    {code} — {label}
                  </option>
                ))}
              </select>
            </label>
          )
        })}
      </div>
    )
  }

  return (
    <div>
      <h3>{kind === 'diagnostico' ? 'Odontograma de diagnóstico' : 'Odontograma de evolución'}</h3>
      <p className={styles.fieldsetLabel}>Arcada superior</p>
      {renderRow(UPPER_PERMANENT_ROW)}
      <p className={styles.fieldsetLabel}>Arcada inferior</p>
      {renderRow(LOWER_PERMANENT_ROW)}
    </div>
  )
}

function ToothDiagnosisCodeSection({
  patientId,
  canWrite,
  encounterPicker,
}: {
  patientId: string
  canWrite: boolean
  encounterPicker: EncounterPicker
}) {
  const queryClient = useQueryClient()
  const { encounterId } = encounterPicker

  const diagnosisQuery = useQuery({
    queryKey: ['endo-history-tooth-diagnosis-code', patientId, 'diagnostico'],
    queryFn: () => endoApi.listToothDiagnosisCodes(patientId, 'diagnostico'),
  })
  const evolucionQuery = useQuery({
    queryKey: ['endo-history-tooth-diagnosis-code', patientId, 'evolucion'],
    queryFn: () => endoApi.listToothDiagnosisCodes(patientId, 'evolucion'),
  })

  function invalidateBoth() {
    queryClient.invalidateQueries({
      queryKey: ['endo-history-tooth-diagnosis-code', patientId, 'diagnostico'],
    })
    queryClient.invalidateQueries({
      queryKey: ['endo-history-tooth-diagnosis-code', patientId, 'evolucion'],
    })
  }

  return (
    // Correccion: esta es la UNICA seccion de la pestana que renderiza el
    // EncounterPickerField -- cerrarla por defecto (ronda 2.1) dejaba sin
    // forma de seleccionar/iniciar una atencion a quien no la abriera
    // primero, deshabilitando en silencio TODO lo demas en Historia de
    // Endodoncia.
    <details className={`${styles.card} ${styles.fullWidth}`} open>
      <summary>Odontograma de diagnóstico y evolución (18 códigos)</summary>

      {canWrite && <EncounterPickerField encounterPicker={encounterPicker} />}
      {!encounterId && (
        <p className={styles.complianceNote}>
          Selecciona o inicia una atención para poder capturar códigos en el odontograma.
        </p>
      )}

      <ToothCodeGrid
        patientId={patientId}
        canWrite={canWrite}
        encounterId={encounterId}
        kind="diagnostico"
        entries={diagnosisQuery.data ?? []}
        onSaved={invalidateBoth}
      />
      <ToothCodeGrid
        patientId={patientId}
        canWrite={canWrite}
        encounterId={encounterId}
        kind="evolucion"
        entries={evolucionQuery.data ?? []}
        onSaved={invalidateBoth}
      />

      <p className={styles.complianceNote}>
        Catálogo de 18 códigos (0-17) propio de endodoncia. Al volver a capturar un código para la
        misma pieza, el anterior se anula automáticamente (queda en el historial de auditoría).
      </p>
    </details>
  )
}

// --------------------------------------------------------------------------------
// 7. Longitud de trabajo + datos de tratamiento -- documenta el tratamiento de
// una pieza; cada entrada es independiente (varias piezas a lo largo del
// tiempo), asi que se mantiene el patron "Agregar"/"Anular" simple (sin
// patron "editar": no esta en la lista de secciones de la ronda 2.2).
// --------------------------------------------------------------------------------

const WORKING_LENGTH_DEFAULTS = {
  tooth_fdi: '',
  tecnica_instrumentacion: '',
  tecnica_obturacion: '',
  indicaciones: '',
  fecha_inicio: '',
  fecha_termino: '',
}

function emptyCanalMeasurements(): Record<string, CanalMeasurementDetail> {
  const result: Record<string, CanalMeasurementDetail> = {}
  for (const key of CANAL_KEYS) {
    result[key] = { aparente_rx: '', real_localizador: '', relacion: '' }
  }
  return result
}

function WorkingLengthSection({
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
    queryKey: ['endo-history-working-length', patientId],
    queryFn: () => endoApi.listWorkingLengths(patientId),
  })
  const [form, setForm] = useState(WORKING_LENGTH_DEFAULTS)
  const [canalMeasurements, setCanalMeasurements] = useState(emptyCanalMeasurements)

  function update<K extends keyof typeof WORKING_LENGTH_DEFAULTS>(key: K, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  function updateCanal(key: string, field: keyof CanalMeasurementDetail, value: string) {
    setCanalMeasurements((prev) => ({ ...prev, [key]: { ...prev[key], [field]: value } }))
  }

  const createMutation = useMutation({
    mutationFn: () => {
      const payload: Record<string, CanalMeasurementDetail> = {}
      for (const key of CANAL_KEYS) {
        const m = canalMeasurements[key]
        if (m.aparente_rx || m.real_localizador || m.relacion) {
          payload[key] = {
            aparente_rx: m.aparente_rx || null,
            real_localizador: m.real_localizador || null,
            relacion: m.relacion || null,
          }
        }
      }
      return endoApi.createWorkingLength(patientId, {
        encounter_id: encounterId,
        tooth_fdi: form.tooth_fdi || null,
        canal_measurements: payload,
        tecnica_instrumentacion: form.tecnica_instrumentacion || null,
        tecnica_obturacion: form.tecnica_obturacion || null,
        indicaciones: form.indicaciones || null,
        fecha_inicio: form.fecha_inicio || null,
        fecha_termino: form.fecha_termino || null,
      })
    },
    onSuccess: () => {
      setForm(WORKING_LENGTH_DEFAULTS)
      setCanalMeasurements(emptyCanalMeasurements())
      queryClient.invalidateQueries({ queryKey: ['endo-history-working-length', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      endoApi.annulWorkingLength(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['endo-history-working-length', patientId] })
    },
  })

  function detailRows(item: EndodonticWorkingLengthOut): [string, string][] {
    const rows: [string, string][] = []
    if (item.tooth_fdi) rows.push(['Pieza', item.tooth_fdi])
    for (const key of CANAL_KEYS) {
      const m = item.canal_measurements[key]
      if (m && (m.aparente_rx || m.real_localizador || m.relacion)) {
        const parts = [m.aparente_rx, m.real_localizador, m.relacion].filter(Boolean)
        rows.push([CANAL_LABELS[key], parts.join(' · ')])
      }
    }
    if (item.tecnica_instrumentacion) rows.push(['Técnica de instrumentación', item.tecnica_instrumentacion])
    if (item.tecnica_obturacion) rows.push(['Técnica de obturación', item.tecnica_obturacion])
    if (item.indicaciones) rows.push(['Indicaciones', item.indicaciones])
    if (item.fecha_inicio) rows.push(['Fecha de inicio', item.fecha_inicio])
    if (item.fecha_termino) rows.push(['Fecha de término', item.fecha_termino])
    return rows
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Longitud de trabajo
        <MissingDataBadge hasActiveEntries={activeEntries.length > 0} />
      </summary>
      {listQuery.data?.map((item) => (
        <div key={item.id} className={styles.contactItem}>
          <div>
            <p>
              {new Date(item.created_at).toLocaleString('es-MX')}
              {!item.is_active && ' (anulado)'}
            </p>
            <DetailList rows={detailRows(item)} />
          </div>
          {canWrite && item.is_active && (
            <AnnulButton onAnnul={(reason) => annulMutation.mutate({ itemId: item.id, reason })} />
          )}
        </div>
      ))}
      {listQuery.data?.length === 0 && <p>Sin longitud de trabajo registrada.</p>}

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
            placeholder="Pieza FDI (opcional)"
            maxLength={2}
            value={form.tooth_fdi}
            onChange={(e) => update('tooth_fdi', e.target.value)}
          />
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Conducto</th>
                  <th>Aparente (Rx)</th>
                  <th>Real (localizador)</th>
                  <th>Relación</th>
                </tr>
              </thead>
              <tbody>
                {CANAL_KEYS.map((key) => (
                  <tr key={key}>
                    <td>{CANAL_LABELS[key]}</td>
                    <td>
                      <input
                        type="text"
                        aria-label={`${CANAL_LABELS[key]}: aparente (Rx)`}
                        value={canalMeasurements[key]?.aparente_rx ?? ''}
                        onChange={(e) => updateCanal(key, 'aparente_rx', e.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        type="text"
                        aria-label={`${CANAL_LABELS[key]}: real (localizador)`}
                        value={canalMeasurements[key]?.real_localizador ?? ''}
                        onChange={(e) => updateCanal(key, 'real_localizador', e.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        type="text"
                        aria-label={`${CANAL_LABELS[key]}: relación`}
                        value={canalMeasurements[key]?.relacion ?? ''}
                        onChange={(e) => updateCanal(key, 'relacion', e.target.value)}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <input
            type="text"
            placeholder="Técnica de instrumentación (opcional)"
            value={form.tecnica_instrumentacion}
            onChange={(e) => update('tecnica_instrumentacion', e.target.value)}
          />
          <input
            type="text"
            placeholder="Técnica de obturación (opcional)"
            value={form.tecnica_obturacion}
            onChange={(e) => update('tecnica_obturacion', e.target.value)}
          />
          <input
            type="text"
            placeholder="Indicaciones (opcional)"
            value={form.indicaciones}
            onChange={(e) => update('indicaciones', e.target.value)}
          />
          <input
            type="text"
            placeholder="Fecha de inicio (opcional)"
            value={form.fecha_inicio}
            onChange={(e) => update('fecha_inicio', e.target.value)}
          />
          <input
            type="text"
            placeholder="Fecha de término (opcional)"
            value={form.fecha_termino}
            onChange={(e) => update('fecha_termino', e.target.value)}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            Guardar longitud de trabajo
          </button>
        </form>
      )}
    </details>
  )
}

/** PDF: mismo patron que GeneralHistoryPdfButton/OdontologicalHistoryPdfButton
 * -- window.open sincronico antes del await para no perder el gesto del
 * usuario. */
function EndodonticHistoryPdfButton({ patientId }: { patientId: string }) {
  const [error, setError] = useState(false)
  const [generating, setGenerating] = useState(false)

  async function handleClick() {
    setError(false)
    setGenerating(true)
    const newTab = window.open('', '_blank')
    try {
      const url = await endoApi.getEndodonticHistoryPdfBlobUrl(patientId)
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

export function EndodonticHistoryTab({
  patientId,
  canWrite,
  encounterPicker,
}: {
  patientId: string
  canWrite: boolean
  encounterPicker: EncounterPicker
}) {
  const { encounterId } = encounterPicker

  return (
    <>
      <EndodonticHistoryPdfButton patientId={patientId} />
      <InterrogationSection patientId={patientId} canWrite={canWrite} encounterId={encounterId} />
      <PulpSensitivityTestSection patientId={patientId} canWrite={canWrite} encounterId={encounterId} />
      <PeriodontalTestSection patientId={patientId} canWrite={canWrite} encounterId={encounterId} />
      <RadiographicInterpretationSection
        patientId={patientId}
        canWrite={canWrite}
        encounterId={encounterId}
      />
      <DiagnosisTreatmentSection patientId={patientId} canWrite={canWrite} encounterId={encounterId} />
      <ToothDiagnosisCodeSection
        patientId={patientId}
        canWrite={canWrite}
        encounterPicker={encounterPicker}
      />
      <WorkingLengthSection patientId={patientId} canWrite={canWrite} encounterId={encounterId} />
    </>
  )
}
