import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { canReadOdontogram, canWriteOdontogram } from '../auth/roles'
import { useActiveRole } from '../auth/store'
import * as catalogsApi from '../catalogs/api'
import type { CatalogItemOut } from '../catalogs/types'
import { EncounterPickerField } from '../encounters/EncounterPicker'
import type { EncounterPicker } from '../encounters/useEncounterPicker'
import * as odontoApi from '../odontologicalHistory/api'
import type { ToothTreatmentPlanEntryOut } from '../odontologicalHistory/types'
import { Odontograma } from '../odontogram/Odontograma'
import { PediatricOdontogramaAnnotations } from '../odontogram/PediatricOdontogramaAnnotations'
import {
  LOWER_PERMANENT_ROW,
  LOWER_TEMPORARY_ROW,
  UPPER_PERMANENT_ROW,
  UPPER_TEMPORARY_ROW,
} from '../odontogram/toothRules'
import * as pedApi from '../pediatricHistory/api'
import {
  BEHAVIOR_BOOLEAN_FIELDS,
  ERUPTION_BOOLEAN_FIELDS,
  LINEA_MEDIA_LABELS,
  ORAL_HABITS_FIELDS,
  PERMANENT_TOOTH_ERUPTION_CHRONOLOGY,
  PRIMARY_TOOTH_ERUPTION_CHRONOLOGY,
  type ClasificacionAngle,
  type LineaMedia,
  type PediatricBehaviorMaturityOut,
  type PediatricEruptionDentitionOut,
  type PediatricOcclusionOut,
  type PediatricOralHabitsCreateInput,
  type PediatricOralHabitsField,
  type PediatricOralHabitsOut,
  type PediatricPerinatalHistoryOut,
  type PediatricToothAnnotationOut,
} from '../pediatricHistory/types'
import { latestActive, saveWithAutoCorrection, triStateRow } from './historyHelpers'
import { AnnulButton, DetailList, EditingBanner, MissingDataBadge, TriStateRadioGroup } from './historyShared'
import styles from './PatientDetailPage.module.css'

/** Fase E (rediseno del expediente, docs/clinica): Historia Clinica
 * Pediatrica -- sigue el mismo patron ya establecido en
 * OdontologicalHistoryTab.tsx (Fase C): secciones <details> cerradas por
 * defecto con badge "Faltan datos", vista "ya guardado" tipo <dl> con todos
 * los campos capturados, fecha de captura visible, y una sola atencion
 * compartida con un solo picker "ancla" (aqui: Odontograma pediatrico +
 * anotaciones por pieza, la seccion con mas interaccion). */

// --------------------------------------------------------------------------------
// 1. Antecedentes perinatales y primer ano de vida.
// --------------------------------------------------------------------------------

const PERINATAL_DEFAULTS = {
  problemas_embarazo_perinatales: '',
  tomo_medicamentos_embarazo: null as boolean | null,
  tomo_medicamentos_embarazo_cuales: '',
  embarazo_observaciones: '',
  tomo_medicamentos_primer_ano: null as boolean | null,
  tomo_medicamentos_primer_ano_cuales: '',
  vacunas_completas: null as boolean | null,
  fecha_ultima_visita_dentista: '',
}

function PerinatalHistorySection({
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
    queryKey: ['pediatric-history-perinatal', patientId],
    queryFn: () => pedApi.listPerinatalHistories(patientId),
  })
  const [form, setForm] = useState(PERINATAL_DEFAULTS)

  function update<K extends keyof typeof PERINATAL_DEFAULTS>(key: K, value: (typeof PERINATAL_DEFAULTS)[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  // Correccion UX (ronda 2.2): entrada activa mas reciente -- se precarga el
  // formulario para "editarla" (anular+recapturar por dentro).
  const current = latestActive(listQuery.data)

  useEffect(() => {
    if (current) {
      // Correccion UX (ronda 2.2): precarga intencional del formulario al
      // cambiar la entrada activa a editar -- no es sincronizacion con un
      // sistema externo, por eso se suprime la regla.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setForm({
        problemas_embarazo_perinatales: current.problemas_embarazo_perinatales ?? '',
        tomo_medicamentos_embarazo: current.tomo_medicamentos_embarazo,
        tomo_medicamentos_embarazo_cuales: current.tomo_medicamentos_embarazo_cuales ?? '',
        embarazo_observaciones: current.embarazo_observaciones ?? '',
        tomo_medicamentos_primer_ano: current.tomo_medicamentos_primer_ano,
        tomo_medicamentos_primer_ano_cuales: current.tomo_medicamentos_primer_ano_cuales ?? '',
        vacunas_completas: current.vacunas_completas,
        fecha_ultima_visita_dentista: current.fecha_ultima_visita_dentista ?? '',
      })
    } else {
      setForm(PERINATAL_DEFAULTS)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        current,
        (itemId, reason) => pedApi.annulPerinatalHistory(patientId, itemId, reason),
        () =>
          pedApi.createPerinatalHistory(patientId, {
            encounter_id: encounterId,
            problemas_embarazo_perinatales: form.problemas_embarazo_perinatales || null,
            tomo_medicamentos_embarazo: form.tomo_medicamentos_embarazo,
            tomo_medicamentos_embarazo_cuales: form.tomo_medicamentos_embarazo_cuales || null,
            embarazo_observaciones: form.embarazo_observaciones || null,
            tomo_medicamentos_primer_ano: form.tomo_medicamentos_primer_ano,
            tomo_medicamentos_primer_ano_cuales: form.tomo_medicamentos_primer_ano_cuales || null,
            vacunas_completas: form.vacunas_completas,
            fecha_ultima_visita_dentista: form.fecha_ultima_visita_dentista || null,
          }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pediatric-history-perinatal', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      pedApi.annulPerinatalHistory(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pediatric-history-perinatal', patientId] })
    },
  })

  function detailRows(item: PediatricPerinatalHistoryOut): [string, string][] {
    const rows: ([string, string] | null)[] = [
      item.problemas_embarazo_perinatales
        ? ['Problemas durante el embarazo o perinatales', item.problemas_embarazo_perinatales]
        : null,
      triStateRow('Tomo medicamentos durante el embarazo', item.tomo_medicamentos_embarazo),
      item.tomo_medicamentos_embarazo_cuales
        ? ['Cuales (embarazo)', item.tomo_medicamentos_embarazo_cuales]
        : null,
      item.embarazo_observaciones ? ['Observaciones del embarazo', item.embarazo_observaciones] : null,
      triStateRow('Tomo medicamentos durante el primer año de vida', item.tomo_medicamentos_primer_ano),
      item.tomo_medicamentos_primer_ano_cuales
        ? ['Cuales (primer año de vida)', item.tomo_medicamentos_primer_ano_cuales]
        : null,
      triStateRow('Esquema de vacunación completo', item.vacunas_completas),
      item.fecha_ultima_visita_dentista
        ? ['Última visita al dentista', item.fecha_ultima_visita_dentista]
        : null,
    ]
    return rows.filter((r): r is [string, string] => r !== null)
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Antecedentes perinatales y primer año de vida
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
      {listQuery.data?.length === 0 && <p>Sin antecedentes perinatales registrados.</p>}

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
            placeholder="Problemas durante el embarazo o perinatales (opcional)"
            value={form.problemas_embarazo_perinatales}
            onChange={(e) => update('problemas_embarazo_perinatales', e.target.value)}
          />
          <TriStateRadioGroup
            label="¿Tomó medicamentos durante el embarazo?"
            name="tomo_medicamentos_embarazo"
            value={form.tomo_medicamentos_embarazo}
            onChange={(v) => update('tomo_medicamentos_embarazo', v)}
          />
          <input
            type="text"
            placeholder="¿Cuáles? (opcional)"
            value={form.tomo_medicamentos_embarazo_cuales}
            onChange={(e) => update('tomo_medicamentos_embarazo_cuales', e.target.value)}
          />
          <input
            type="text"
            placeholder="Observaciones del embarazo (opcional)"
            value={form.embarazo_observaciones}
            onChange={(e) => update('embarazo_observaciones', e.target.value)}
          />
          <TriStateRadioGroup
            label="¿Tomó medicamentos durante el primer año de vida?"
            name="tomo_medicamentos_primer_ano"
            value={form.tomo_medicamentos_primer_ano}
            onChange={(v) => update('tomo_medicamentos_primer_ano', v)}
          />
          <input
            type="text"
            placeholder="¿Cuáles? (opcional)"
            value={form.tomo_medicamentos_primer_ano_cuales}
            onChange={(e) => update('tomo_medicamentos_primer_ano_cuales', e.target.value)}
          />
          <TriStateRadioGroup
            label="¿Esquema de vacunación completo?"
            name="vacunas_completas"
            value={form.vacunas_completas}
            onChange={(v) => update('vacunas_completas', v)}
          />
          <input
            type="text"
            placeholder="Fecha de la última visita al dentista (opcional)"
            value={form.fecha_ultima_visita_dentista}
            onChange={(e) => update('fecha_ultima_visita_dentista', e.target.value)}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Guardar antecedentes perinatales'}
          </button>
        </form>
      )}
    </details>
  )
}

// --------------------------------------------------------------------------------
// 2. Habitos y antecedentes bucales.
// --------------------------------------------------------------------------------

function emptyOralHabits(): PediatricOralHabitsCreateInput {
  return {
    encounter_id: '',
    cepilla_despues_alimento: null,
    sangran_encias_sin_cepillar: null,
    sabe_que_es_fluor: null,
    fluoruro_sistematico_aplicado: null,
    diente_extraido: null,
    accidentes_fracturas_dentales: null,
    dolor_dental_reciente: null,
    bruxismo_nocturno: null,
    respira_boca_frecuente: null,
  }
}

function OralHabitsSection({
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
    queryKey: ['pediatric-history-oral-habits', patientId],
    queryFn: () => pedApi.listOralHabits(patientId),
  })
  const [form, setForm] = useState(emptyOralHabits)

  function update(key: PediatricOralHabitsField, value: boolean | null) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  // Correccion UX (ronda 2.2): entrada activa mas reciente -- se precarga el
  // formulario para "editarla" (anular+recapturar por dentro).
  const current = latestActive(listQuery.data)

  useEffect(() => {
    if (current) {
      const next = emptyOralHabits()
      for (const { key } of ORAL_HABITS_FIELDS) {
        next[key] = current[key as keyof PediatricOralHabitsOut] as boolean | null
      }
      // Correccion UX (ronda 2.2): precarga intencional del formulario al
      // cambiar la entrada activa a editar -- no es sincronizacion con un
      // sistema externo, por eso se suprime la regla.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setForm(next)
    } else {
      setForm(emptyOralHabits())
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        current,
        (itemId, reason) => pedApi.annulOralHabits(patientId, itemId, reason),
        () => pedApi.createOralHabits(patientId, { ...form, encounter_id: encounterId }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pediatric-history-oral-habits', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      pedApi.annulOralHabits(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pediatric-history-oral-habits', patientId] })
    },
  })

  function detailRows(item: PediatricOralHabitsOut): [string, string][] {
    return ORAL_HABITS_FIELDS.map(({ key, label }) =>
      triStateRow(label, item[key as keyof PediatricOralHabitsOut] as boolean | null),
    ).filter((r): r is [string, string] => r !== null)
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Hábitos y antecedentes bucales
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
      {listQuery.data?.length === 0 && <p>Sin hábitos bucales registrados.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          {ORAL_HABITS_FIELDS.map(({ key, label }) => (
            <TriStateRadioGroup
              key={key}
              label={label}
              name={key}
              value={form[key] as boolean | null}
              onChange={(v) => update(key, v)}
            />
          ))}
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Guardar hábitos bucales'}
          </button>
        </form>
      )}
    </details>
  )
}

// --------------------------------------------------------------------------------
// 3. Madurez y conducta.
// --------------------------------------------------------------------------------

const BEHAVIOR_TEXT_DEFAULTS = {
  edad_dejo_biberon: '',
  relacion_otros_ninos: '',
  caracter: '',
  observaciones: '',
}

type BehaviorBooleanKey = (typeof BEHAVIOR_BOOLEAN_FIELDS)[number]['key']

function emptyBehaviorBooleans(): Record<BehaviorBooleanKey, boolean | null> {
  const result = {} as Record<BehaviorBooleanKey, boolean | null>
  for (const { key } of BEHAVIOR_BOOLEAN_FIELDS) {
    result[key] = null
  }
  return result
}

function BehaviorMaturitySection({
  patientId,
  canWrite,
  encounterId,
  characterCatalog,
}: {
  patientId: string
  canWrite: boolean
  encounterId: string
  characterCatalog: CatalogItemOut[]
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['pediatric-history-behavior-maturity', patientId],
    queryFn: () => pedApi.listBehaviorMaturities(patientId),
  })
  const [booleans, setBooleans] = useState(emptyBehaviorBooleans)
  const [text, setText] = useState(BEHAVIOR_TEXT_DEFAULTS)

  function updateBoolean(key: keyof typeof booleans, value: boolean | null) {
    setBooleans((prev) => ({ ...prev, [key]: value }))
  }
  function updateText<K extends keyof typeof BEHAVIOR_TEXT_DEFAULTS>(key: K, value: string) {
    setText((prev) => ({ ...prev, [key]: value }))
  }

  // Correccion UX (ronda 2.2): entrada activa mas reciente -- se precarga el
  // formulario para "editarla" (anular+recapturar por dentro).
  const current = latestActive(listQuery.data)

  useEffect(() => {
    if (current) {
      const nextBooleans = emptyBehaviorBooleans()
      for (const { key } of BEHAVIOR_BOOLEAN_FIELDS) {
        nextBooleans[key] = current[key as keyof PediatricBehaviorMaturityOut] as boolean | null
      }
      // Correccion UX (ronda 2.2): precarga intencional del formulario al
      // cambiar la entrada activa a editar -- no es sincronizacion con un
      // sistema externo, por eso se suprime la regla.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setBooleans(nextBooleans)
      setText({
        edad_dejo_biberon: current.edad_dejo_biberon ?? '',
        relacion_otros_ninos: current.relacion_otros_ninos ?? '',
        caracter: current.caracter ?? '',
        observaciones: current.observaciones ?? '',
      })
    } else {
      setBooleans(emptyBehaviorBooleans())
      setText(BEHAVIOR_TEXT_DEFAULTS)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        current,
        (itemId, reason) => pedApi.annulBehaviorMaturity(patientId, itemId, reason),
        () =>
          pedApi.createBehaviorMaturity(patientId, {
            encounter_id: encounterId,
            ...booleans,
            edad_dejo_biberon: text.edad_dejo_biberon || null,
            relacion_otros_ninos: text.relacion_otros_ninos || null,
            caracter: text.caracter || null,
            observaciones: text.observaciones || null,
          }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pediatric-history-behavior-maturity', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      pedApi.annulBehaviorMaturity(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pediatric-history-behavior-maturity', patientId] })
    },
  })

  function characterLabel(code: string | null): string | null {
    if (!code) return null
    return characterCatalog.find((c) => c.code === code)?.name ?? code
  }

  function detailRows(item: PediatricBehaviorMaturityOut): [string, string][] {
    const rows: ([string, string] | null)[] = [
      ...BEHAVIOR_BOOLEAN_FIELDS.map(({ key, label }) =>
        triStateRow(label, item[key as keyof PediatricBehaviorMaturityOut] as boolean | null),
      ),
      item.edad_dejo_biberon ? ['Edad en que dejó el biberón', item.edad_dejo_biberon] : null,
      item.relacion_otros_ninos ? ['Relación con otros niños', item.relacion_otros_ninos] : null,
      characterLabel(item.caracter) ? ['Carácter', characterLabel(item.caracter) as string] : null,
      item.observaciones ? ['Observaciones', item.observaciones] : null,
    ]
    return rows.filter((r): r is [string, string] => r !== null)
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Madurez y conducta
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
      {listQuery.data?.length === 0 && <p>Sin datos de madurez y conducta registrados.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          {BEHAVIOR_BOOLEAN_FIELDS.map(({ key, label }) => (
            <TriStateRadioGroup
              key={key}
              label={label}
              name={key}
              value={booleans[key]}
              onChange={(v) => updateBoolean(key, v)}
            />
          ))}
          <input
            type="text"
            placeholder="Edad en que dejó el biberón (opcional)"
            value={text.edad_dejo_biberon}
            onChange={(e) => updateText('edad_dejo_biberon', e.target.value)}
          />
          <input
            type="text"
            placeholder="Relación con otros niños (opcional)"
            value={text.relacion_otros_ninos}
            onChange={(e) => updateText('relacion_otros_ninos', e.target.value)}
          />
          <select
            aria-label="Carácter"
            value={text.caracter}
            onChange={(e) => updateText('caracter', e.target.value)}
          >
            <option value="">Carácter: sin especificar</option>
            {characterCatalog.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Observaciones (opcional)"
            value={text.observaciones}
            onChange={(e) => updateText('observaciones', e.target.value)}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Guardar madurez y conducta'}
          </button>
        </form>
      )}
    </details>
  )
}

// --------------------------------------------------------------------------------
// 4. Oclusion y alineamiento.
// --------------------------------------------------------------------------------

const OCCLUSION_DEFAULTS = {
  planos_terminales_izq: '',
  planos_terminales_der: '',
  angle_molar_izq: '',
  angle_molar_der: '',
  overjet_mm: '',
  overbite_mm: '',
  mordida_cruzada: null as boolean | null,
  diastema: null as boolean | null,
  mordida_abierta_ante_mm: '',
  mordida_abierta_post_mm: '',
  linea_media: '' as LineaMedia | '',
  clasificacion_angle: '' as ClasificacionAngle | '',
}

function OcclusionSection({
  patientId,
  canWrite,
  encounterId,
  terminalPlaneCatalog,
}: {
  patientId: string
  canWrite: boolean
  encounterId: string
  terminalPlaneCatalog: CatalogItemOut[]
}) {
  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['pediatric-history-occlusion', patientId],
    queryFn: () => pedApi.listOcclusions(patientId),
  })
  const [form, setForm] = useState(OCCLUSION_DEFAULTS)

  function update<K extends keyof typeof OCCLUSION_DEFAULTS>(key: K, value: (typeof OCCLUSION_DEFAULTS)[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  // Correccion UX (ronda 2.2): entrada activa mas reciente -- se precarga el
  // formulario para "editarla" (anular+recapturar por dentro).
  const current = latestActive(listQuery.data)

  useEffect(() => {
    if (current) {
      // Correccion UX (ronda 2.2): precarga intencional del formulario al
      // cambiar la entrada activa a editar -- no es sincronizacion con un
      // sistema externo, por eso se suprime la regla.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setForm({
        planos_terminales_izq: current.planos_terminales_izq ?? '',
        planos_terminales_der: current.planos_terminales_der ?? '',
        angle_molar_izq: current.angle_molar_izq ?? '',
        angle_molar_der: current.angle_molar_der ?? '',
        overjet_mm: current.overjet_mm != null ? String(current.overjet_mm) : '',
        overbite_mm: current.overbite_mm != null ? String(current.overbite_mm) : '',
        mordida_cruzada: current.mordida_cruzada,
        diastema: current.diastema,
        mordida_abierta_ante_mm:
          current.mordida_abierta_ante_mm != null ? String(current.mordida_abierta_ante_mm) : '',
        mordida_abierta_post_mm:
          current.mordida_abierta_post_mm != null ? String(current.mordida_abierta_post_mm) : '',
        linea_media: current.linea_media ?? '',
        clasificacion_angle: current.clasificacion_angle ?? '',
      })
    } else {
      setForm(OCCLUSION_DEFAULTS)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        current,
        (itemId, reason) => pedApi.annulOcclusion(patientId, itemId, reason),
        () =>
          pedApi.createOcclusion(patientId, {
            encounter_id: encounterId,
            planos_terminales_izq: form.planos_terminales_izq || null,
            planos_terminales_der: form.planos_terminales_der || null,
            angle_molar_izq: form.angle_molar_izq || null,
            angle_molar_der: form.angle_molar_der || null,
            overjet_mm: form.overjet_mm ? Number(form.overjet_mm) : null,
            overbite_mm: form.overbite_mm ? Number(form.overbite_mm) : null,
            mordida_cruzada: form.mordida_cruzada,
            diastema: form.diastema,
            mordida_abierta_ante_mm: form.mordida_abierta_ante_mm
              ? Number(form.mordida_abierta_ante_mm)
              : null,
            mordida_abierta_post_mm: form.mordida_abierta_post_mm
              ? Number(form.mordida_abierta_post_mm)
              : null,
            linea_media: form.linea_media || null,
            clasificacion_angle: form.clasificacion_angle || null,
          }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pediatric-history-occlusion', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      pedApi.annulOcclusion(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pediatric-history-occlusion', patientId] })
    },
  })

  function catalogLabel(code: string | null): string | null {
    if (!code) return null
    return terminalPlaneCatalog.find((c) => c.code === code)?.name ?? code
  }

  function detailRows(item: PediatricOcclusionOut): [string, string][] {
    const rows: ([string, string] | null)[] = [
      catalogLabel(item.planos_terminales_izq)
        ? ['Plano terminal izquierdo', catalogLabel(item.planos_terminales_izq) as string]
        : null,
      catalogLabel(item.planos_terminales_der)
        ? ['Plano terminal derecho', catalogLabel(item.planos_terminales_der) as string]
        : null,
      item.angle_molar_izq ? ['Relación molar de Angle izquierda', item.angle_molar_izq] : null,
      item.angle_molar_der ? ['Relación molar de Angle derecha', item.angle_molar_der] : null,
      item.overjet_mm != null ? ['Overjet (mm)', String(item.overjet_mm)] : null,
      item.overbite_mm != null ? ['Overbite (mm)', String(item.overbite_mm)] : null,
      triStateRow('Mordida cruzada', item.mordida_cruzada),
      triStateRow('Diastema', item.diastema),
      item.mordida_abierta_ante_mm != null
        ? ['Mordida abierta anterior (mm)', String(item.mordida_abierta_ante_mm)]
        : null,
      item.mordida_abierta_post_mm != null
        ? ['Mordida abierta posterior (mm)', String(item.mordida_abierta_post_mm)]
        : null,
      item.linea_media ? ['Línea media', LINEA_MEDIA_LABELS[item.linea_media]] : null,
      item.clasificacion_angle
        ? ['Clasificación de Angle', `Clase ${item.clasificacion_angle}`]
        : null,
    ]
    return rows.filter((r): r is [string, string] => r !== null)
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Oclusión y alineamiento
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
      {listQuery.data?.length === 0 && <p>Sin datos de oclusión registrados.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <label className={styles.fieldRow}>
            <span>Plano terminal izquierdo</span>
            <select
              aria-label="Plano terminal izquierdo"
              value={form.planos_terminales_izq}
              onChange={(e) => update('planos_terminales_izq', e.target.value)}
            >
              <option value="">Sin especificar</option>
              {terminalPlaneCatalog.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.fieldRow}>
            <span>Plano terminal derecho</span>
            <select
              aria-label="Plano terminal derecho"
              value={form.planos_terminales_der}
              onChange={(e) => update('planos_terminales_der', e.target.value)}
            >
              <option value="">Sin especificar</option>
              {terminalPlaneCatalog.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <input
            type="text"
            placeholder="Relación molar de Angle izquierda (opcional)"
            value={form.angle_molar_izq}
            onChange={(e) => update('angle_molar_izq', e.target.value)}
          />
          <input
            type="text"
            placeholder="Relación molar de Angle derecha (opcional)"
            value={form.angle_molar_der}
            onChange={(e) => update('angle_molar_der', e.target.value)}
          />
          <label className={styles.fieldRow}>
            <span>Overjet (mm)</span>
            <input
              type="number"
              step="0.1"
              min="0"
              max="30"
              aria-label="Overjet (mm)"
              value={form.overjet_mm}
              onChange={(e) => update('overjet_mm', e.target.value)}
            />
          </label>
          <label className={styles.fieldRow}>
            <span>Overbite (mm)</span>
            <input
              type="number"
              step="0.1"
              min="-10"
              max="30"
              aria-label="Overbite (mm)"
              value={form.overbite_mm}
              onChange={(e) => update('overbite_mm', e.target.value)}
            />
          </label>
          <TriStateRadioGroup
            label="¿Mordida cruzada?"
            name="mordida_cruzada"
            value={form.mordida_cruzada}
            onChange={(v) => update('mordida_cruzada', v)}
          />
          <TriStateRadioGroup
            label="¿Diastema?"
            name="diastema"
            value={form.diastema}
            onChange={(v) => update('diastema', v)}
          />
          <label className={styles.fieldRow}>
            <span>Mordida abierta anterior (mm)</span>
            <input
              type="number"
              step="0.1"
              min="0"
              max="30"
              aria-label="Mordida abierta anterior (mm)"
              value={form.mordida_abierta_ante_mm}
              onChange={(e) => update('mordida_abierta_ante_mm', e.target.value)}
            />
          </label>
          <label className={styles.fieldRow}>
            <span>Mordida abierta posterior (mm)</span>
            <input
              type="number"
              step="0.1"
              min="0"
              max="30"
              aria-label="Mordida abierta posterior (mm)"
              value={form.mordida_abierta_post_mm}
              onChange={(e) => update('mordida_abierta_post_mm', e.target.value)}
            />
          </label>
          <select
            aria-label="Línea media"
            value={form.linea_media}
            onChange={(e) => update('linea_media', e.target.value as LineaMedia | '')}
          >
            <option value="">Línea media: sin especificar</option>
            {(Object.entries(LINEA_MEDIA_LABELS) as [LineaMedia, string][]).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
          <select
            aria-label="Clasificación de Angle"
            value={form.clasificacion_angle}
            onChange={(e) => update('clasificacion_angle', e.target.value as ClasificacionAngle | '')}
          >
            <option value="">Clasificación de Angle: sin especificar</option>
            {(['I', 'II', 'III'] as ClasificacionAngle[]).map((c) => (
              <option key={c} value={c}>
                Clase {c}
              </option>
            ))}
          </select>
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Guardar oclusión y alineamiento'}
          </button>
        </form>
      )}
    </details>
  )
}

// --------------------------------------------------------------------------------
// 5. Erupcion y denticion.
// --------------------------------------------------------------------------------

type EruptionBooleanKey = (typeof ERUPTION_BOOLEAN_FIELDS)[number]['key']

function emptyEruptionBooleans(): Record<EruptionBooleanKey, boolean | null> {
  const result = {} as Record<EruptionBooleanKey, boolean | null>
  for (const { key } of ERUPTION_BOOLEAN_FIELDS) {
    result[key] = null
  }
  return result
}

const ERUPTION_TEXT_DEFAULTS = {
  otras_anormalidades: '',
  edad_dental: '',
  estado_general_higiene: '',
}

function EruptionDentitionSection({
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
    queryKey: ['pediatric-history-eruption-dentition', patientId],
    queryFn: () => pedApi.listEruptionDentitions(patientId),
  })
  const [booleans, setBooleans] = useState(emptyEruptionBooleans)
  const [text, setText] = useState(ERUPTION_TEXT_DEFAULTS)

  function updateBoolean(key: keyof typeof booleans, value: boolean | null) {
    setBooleans((prev) => ({ ...prev, [key]: value }))
  }
  function updateText<K extends keyof typeof ERUPTION_TEXT_DEFAULTS>(key: K, value: string) {
    setText((prev) => ({ ...prev, [key]: value }))
  }

  // Correccion UX (ronda 2.2): entrada activa mas reciente -- se precarga el
  // formulario para "editarla" (anular+recapturar por dentro).
  const current = latestActive(listQuery.data)

  useEffect(() => {
    if (current) {
      const nextBooleans = emptyEruptionBooleans()
      for (const { key } of ERUPTION_BOOLEAN_FIELDS) {
        nextBooleans[key] = current[key as keyof PediatricEruptionDentitionOut] as boolean | null
      }
      // Correccion UX (ronda 2.2): precarga intencional del formulario al
      // cambiar la entrada activa a editar -- no es sincronizacion con un
      // sistema externo, por eso se suprime la regla.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setBooleans(nextBooleans)
      setText({
        otras_anormalidades: current.otras_anormalidades ?? '',
        edad_dental: current.edad_dental ?? '',
        estado_general_higiene: current.estado_general_higiene ?? '',
      })
    } else {
      setBooleans(emptyEruptionBooleans())
      setText(ERUPTION_TEXT_DEFAULTS)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const createMutation = useMutation({
    mutationFn: () =>
      saveWithAutoCorrection(
        current,
        (itemId, reason) => pedApi.annulEruptionDentition(patientId, itemId, reason),
        () =>
          pedApi.createEruptionDentition(patientId, {
            encounter_id: encounterId,
            ...booleans,
            otras_anormalidades: text.otras_anormalidades || null,
            edad_dental: text.edad_dental || null,
            estado_general_higiene: text.estado_general_higiene || null,
          }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pediatric-history-eruption-dentition', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      pedApi.annulEruptionDentition(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pediatric-history-eruption-dentition', patientId] })
    },
  })

  function detailRows(item: PediatricEruptionDentitionOut): [string, string][] {
    const rows: ([string, string] | null)[] = [
      ...ERUPTION_BOOLEAN_FIELDS.map(({ key, label }) =>
        triStateRow(label, item[key as keyof PediatricEruptionDentitionOut] as boolean | null),
      ),
      item.otras_anormalidades ? ['Otras anormalidades', item.otras_anormalidades] : null,
      item.edad_dental ? ['Edad dental', item.edad_dental] : null,
      item.estado_general_higiene ? ['Estado general de higiene', item.estado_general_higiene] : null,
    ]
    return rows.filter((r): r is [string, string] => r !== null)
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Erupción y dentición
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
      {listQuery.data?.length === 0 && <p>Sin datos de erupción y dentición registrados.</p>}

      {canWrite && current && <EditingBanner createdAt={current.created_at} />}
      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          {ERUPTION_BOOLEAN_FIELDS.map(({ key, label }) => (
            <TriStateRadioGroup
              key={key}
              label={label}
              name={key}
              value={booleans[key]}
              onChange={(v) => updateBoolean(key, v)}
            />
          ))}
          <input
            type="text"
            placeholder="Otras anormalidades (opcional)"
            value={text.otras_anormalidades}
            onChange={(e) => updateText('otras_anormalidades', e.target.value)}
          />
          <input
            type="text"
            placeholder="Edad dental (opcional)"
            value={text.edad_dental}
            onChange={(e) => updateText('edad_dental', e.target.value)}
          />
          <input
            type="text"
            placeholder="Estado general de higiene (opcional)"
            value={text.estado_general_higiene}
            onChange={(e) => updateText('estado_general_higiene', e.target.value)}
          />
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            {current ? 'Guardar cambios' : 'Guardar erupción y dentición'}
          </button>
        </form>
      )}

      <h3>Cronología de erupción y caída (tabla de referencia)</h3>
      <p className={styles.complianceNote}>
        Tabla fija de consulta (no se captura aquí) -- cronología estándar de odontopediatría.
      </p>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <caption>Dientes temporales</caption>
          <thead>
            <tr>
              <th>Diente</th>
              <th>Erupción</th>
              <th>Caída</th>
            </tr>
          </thead>
          <tbody>
            {PRIMARY_TOOTH_ERUPTION_CHRONOLOGY.map((row) => (
              <tr key={row.diente}>
                <td>{row.diente}</td>
                <td>{row.erupcion}</td>
                <td>{row.caida}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <caption>Dientes permanentes</caption>
          <thead>
            <tr>
              <th>Diente</th>
              <th>Erupción</th>
            </tr>
          </thead>
          <tbody>
            {PERMANENT_TOOTH_ERUPTION_CHRONOLOGY.map((row) => (
              <tr key={row.diente}>
                <td>{row.diente}</td>
                <td>{row.erupcion}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}

// --------------------------------------------------------------------------------
// 6. Odontograma pediatrico + anotaciones por pieza -- seccion "ancla": abierta
// por defecto, sin badge de "Faltan datos", y es la UNICA seccion de esta
// pestana que renderiza el EncounterPickerField (mismo criterio que el
// Odontograma de diagnostico en Fase C).
// --------------------------------------------------------------------------------

const TOOTH_OPTION_GROUPS: { label: string; teeth: number[] }[] = [
  { label: 'Permanentes superiores', teeth: UPPER_PERMANENT_ROW },
  { label: 'Temporales superiores', teeth: UPPER_TEMPORARY_ROW },
  { label: 'Permanentes inferiores', teeth: LOWER_PERMANENT_ROW },
  { label: 'Temporales inferiores', teeth: LOWER_TEMPORARY_ROW },
]

function PediatricOdontogramSection({
  patientId,
  canWrite,
  encounterPicker,
  anomalyCatalog,
}: {
  patientId: string
  canWrite: boolean
  encounterPicker: EncounterPicker
  anomalyCatalog: CatalogItemOut[]
}) {
  const activeRole = useActiveRole()
  const canReadOdo = canReadOdontogram(activeRole)
  const canWriteOdo = canWriteOdontogram(activeRole)

  const queryClient = useQueryClient()
  const listQuery = useQuery({
    queryKey: ['pediatric-history-tooth-annotation', patientId],
    queryFn: () => pedApi.listToothAnnotations(patientId),
  })

  const { encounterId } = encounterPicker
  const [toothFdi, setToothFdi] = useState('')
  const [anomalyCode, setAnomalyCode] = useState('')
  const [hipoplasiaDetail, setHipoplasiaDetail] = useState('')

  const createMutation = useMutation({
    mutationFn: () =>
      pedApi.createToothAnnotation(patientId, {
        encounter_id: encounterId,
        tooth_fdi: toothFdi,
        anomaly_code: anomalyCode,
        hipoplasia_detail: anomalyCode === 'hipoplasia' ? hipoplasiaDetail || null : null,
      }),
    onSuccess: () => {
      setToothFdi('')
      setAnomalyCode('')
      setHipoplasiaDetail('')
      queryClient.invalidateQueries({ queryKey: ['pediatric-history-tooth-annotation', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      pedApi.annulToothAnnotation(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pediatric-history-tooth-annotation', patientId] })
    },
  })

  function anomalyLabel(code: string): string {
    return anomalyCatalog.find((c) => c.code === code)?.name ?? code
  }

  const allEntries = listQuery.data ?? []
  const activeAnnotations = allEntries.filter((a) => a.is_active)

  // Agrupa (activas e inactivas) por pieza para la lista "ya guardado" --
  // el overlay del odontograma de arriba solo usa las activas.
  const entriesByTooth = new Map<string, PediatricToothAnnotationOut[]>()
  for (const entry of allEntries) {
    const list = entriesByTooth.get(entry.tooth_fdi) ?? []
    list.push(entry)
    entriesByTooth.set(entry.tooth_fdi, list)
  }
  const teethWithEntries = [...entriesByTooth.keys()].sort()

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>Odontograma pediátrico (dentición mixta) y anotaciones por pieza</summary>

      {canReadOdo ? (
        <Odontograma patientId={patientId} canWrite={canWriteOdo} />
      ) : (
        <p>No tienes permiso para ver el odontograma.</p>
      )}

      <PediatricOdontogramaAnnotations annotations={activeAnnotations} catalog={anomalyCatalog} />

      <h3>Anotaciones por pieza registradas</h3>
      {teethWithEntries.length === 0 && <p>Sin anotaciones por pieza registradas.</p>}
      {teethWithEntries.map((tooth) => (
        <div key={tooth} className={styles.contactItem}>
          <div>
            <p className={styles.fieldsetLabel}>Pieza {tooth}</p>
            <DetailList
              rows={(entriesByTooth.get(tooth) ?? []).map((entry): [string, string] => [
                `${anomalyLabel(entry.anomaly_code)}${entry.hipoplasia_detail ? ` — ${entry.hipoplasia_detail}` : ''}`,
                `${new Date(entry.created_at).toLocaleString('es-MX')}${entry.is_active ? '' : ' (anulado)'}`,
              ])}
            />
          </div>
          {canWrite &&
            (entriesByTooth.get(tooth) ?? [])
              .filter((entry) => entry.is_active)
              .map((entry) => (
                <AnnulButton
                  key={entry.id}
                  onAnnul={(reason) => annulMutation.mutate({ itemId: entry.id, reason })}
                />
              ))}
        </div>
      ))}

      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <EncounterPickerField encounterPicker={encounterPicker} />

          <p className={styles.fieldsetLabel}>Anotar una pieza</p>
          <select
            aria-label="Pieza FDI a anotar"
            value={toothFdi}
            onChange={(e) => setToothFdi(e.target.value)}
          >
            <option value="">Selecciona una pieza...</option>
            {TOOTH_OPTION_GROUPS.map((group) => (
              <optgroup key={group.label} label={group.label}>
                {group.teeth.map((tooth) => (
                  <option key={tooth} value={String(tooth)}>
                    {tooth}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
          <select
            aria-label="Anomalía"
            value={anomalyCode}
            onChange={(e) => setAnomalyCode(e.target.value)}
          >
            <option value="">Selecciona una anomalía...</option>
            {anomalyCatalog.map((item) => (
              <option key={item.code} value={item.code}>
                {item.name}
              </option>
            ))}
          </select>
          {anomalyCode === 'hipoplasia' && (
            <input
              type="text"
              placeholder="Detalle de la hipoplasia (opcional)"
              value={hipoplasiaDetail}
              onChange={(e) => setHipoplasiaDetail(e.target.value)}
            />
          )}
          <button
            className={styles.primaryButton}
            type="submit"
            disabled={!encounterId || !toothFdi || !anomalyCode || createMutation.isPending}
            title={!encounterId ? 'Selecciona o inicia una atencion' : undefined}
          >
            Anotar
          </button>
        </form>
      )}
    </details>
  )
}

// --------------------------------------------------------------------------------
// 7. Plan de tratamiento por organo dental (pediatrico) -- REUTILIZA el mismo
// endpoint de Fase C (odontologicalHistory/api.ts, tooth-treatment-plan): el
// backend ya acepta piezas temporales ahi. Layout pediatrico: tabla pareada
// pieza permanente + su pieza temporal correspondiente, tal como el PDF.
// --------------------------------------------------------------------------------

interface ToothPairRow {
  permanentTooth: string
  temporaryTooth: string | null
}

function buildQuadrantPairs(permanentQuadrant: number, temporaryQuadrant: number): ToothPairRow[] {
  const rows: ToothPairRow[] = []
  for (let position = 1; position <= 7; position++) {
    rows.push({
      permanentTooth: String(permanentQuadrant * 10 + position),
      temporaryTooth: position <= 5 ? String(temporaryQuadrant * 10 + position) : null,
    })
  }
  return rows
}

const UPPER_TOOTH_PAIRS: ToothPairRow[] = [...buildQuadrantPairs(1, 5), ...buildQuadrantPairs(2, 6)]
const LOWER_TOOTH_PAIRS: ToothPairRow[] = [...buildQuadrantPairs(4, 8), ...buildQuadrantPairs(3, 7)]

function PairedToothPlanFields({
  rows,
  values,
  onChange,
}: {
  rows: ToothPairRow[]
  values: Record<string, string>
  onChange: (tooth: string, value: string) => void
}) {
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Pieza permanente</th>
            <th>Plan (permanente)</th>
            <th>Pieza temporal</th>
            <th>Plan (temporal, opcional)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.permanentTooth}>
              <td>{row.permanentTooth}</td>
              <td>
                <input
                  type="text"
                  aria-label={`Plan de tratamiento pieza ${row.permanentTooth}`}
                  value={values[row.permanentTooth] ?? ''}
                  onChange={(e) => onChange(row.permanentTooth, e.target.value)}
                />
              </td>
              <td>{row.temporaryTooth ?? 'Sin par'}</td>
              <td>
                {row.temporaryTooth && (
                  <input
                    type="text"
                    aria-label={`Plan de tratamiento pieza ${row.temporaryTooth}`}
                    value={values[row.temporaryTooth] ?? ''}
                    onChange={(e) => onChange(row.temporaryTooth as string, e.target.value)}
                  />
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function PediatricToothTreatmentPlanSection({
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
    queryKey: ['odonto-history-tooth-treatment-plan', patientId],
    queryFn: () => odontoApi.listToothTreatmentPlanEntries(patientId),
  })
  const [plans, setPlans] = useState<Record<string, string>>({})
  const [observaciones, setObservaciones] = useState('')

  const createMutation = useMutation({
    mutationFn: () =>
      odontoApi.createToothTreatmentPlanEntry(patientId, {
        encounter_id: encounterId,
        plans: Object.fromEntries(Object.entries(plans).filter(([, v]) => v.trim())),
        observaciones: observaciones || null,
      }),
    onSuccess: () => {
      setPlans({})
      setObservaciones('')
      queryClient.invalidateQueries({ queryKey: ['odonto-history-tooth-treatment-plan', patientId] })
    },
  })

  const annulMutation = useMutation({
    mutationFn: ({ itemId, reason }: { itemId: string; reason: string }) =>
      odontoApi.annulToothTreatmentPlanEntry(patientId, itemId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['odonto-history-tooth-treatment-plan', patientId] })
    },
  })

  function detailRows(item: ToothTreatmentPlanEntryOut): [string, string][] {
    const rows: [string, string][] = Object.entries(item.plans)
      .filter(([, v]) => v)
      .map(([tooth, v]): [string, string] => [`Pieza ${tooth}`, v])
    if (item.observaciones) rows.push(['Observaciones', item.observaciones])
    return rows
  }

  const activeEntries = listQuery.data?.filter((item) => item.is_active) ?? []

  return (
    <details className={`${styles.card} ${styles.fullWidth}`}>
      <summary>
        Plan de tratamiento por órgano dental (pediátrico)
        <MissingDataBadge hasActiveEntries={activeEntries.length > 0} />
      </summary>
      <p className={styles.complianceNote}>
        Comparte los mismos datos que "Plan de tratamiento por órgano dental" de la Historia Clínica
        Odontológica (mismo paciente, mismo registro) -- aquí se muestran pareados con su pieza
        temporal correspondiente, tal como el formato impreso.
      </p>
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
      {listQuery.data?.length === 0 && <p>Sin plan de tratamiento por órgano dental registrado.</p>}

      {canWrite && (
        <form
          className={styles.form}
          onSubmit={(e) => {
            e.preventDefault()
            createMutation.mutate()
          }}
        >
          <p className={styles.fieldsetLabel}>Arcada superior</p>
          <PairedToothPlanFields
            rows={UPPER_TOOTH_PAIRS}
            values={plans}
            onChange={(tooth, value) => setPlans((prev) => ({ ...prev, [tooth]: value }))}
          />
          <p className={styles.fieldsetLabel}>Arcada inferior</p>
          <PairedToothPlanFields
            rows={LOWER_TOOTH_PAIRS}
            values={plans}
            onChange={(tooth, value) => setPlans((prev) => ({ ...prev, [tooth]: value }))}
          />
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
            Guardar plan de tratamiento (pediátrico)
          </button>
        </form>
      )}
    </details>
  )
}

/** PDF: mismo patron que GeneralHistoryPdfButton/OdontologicalHistoryPdfButton
 * -- window.open sincronico antes del await para no perder el gesto del
 * usuario. */
function PediatricHistoryPdfButton({ patientId }: { patientId: string }) {
  const [error, setError] = useState(false)
  const [generating, setGenerating] = useState(false)

  async function handleClick() {
    setError(false)
    setGenerating(true)
    const newTab = window.open('', '_blank')
    try {
      const url = await pedApi.getPediatricHistoryPdfBlobUrl(patientId)
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

export function PediatricHistoryTab({
  patientId,
  canWrite,
  encounterPicker,
}: {
  patientId: string
  canWrite: boolean
  encounterPicker: EncounterPicker
}) {
  const { encounterId } = encounterPicker

  const characterCatalogQuery = useQuery({
    queryKey: ['catalog-items', 'pediatric_character'],
    queryFn: () => catalogsApi.listCatalogItems('pediatric_character', false),
  })
  const terminalPlaneCatalogQuery = useQuery({
    queryKey: ['catalog-items', 'terminal_plane'],
    queryFn: () => catalogsApi.listCatalogItems('terminal_plane', false),
  })
  const anomalyCatalogQuery = useQuery({
    queryKey: ['catalog-items', 'pediatric_tooth_anomaly'],
    queryFn: () => catalogsApi.listCatalogItems('pediatric_tooth_anomaly', false),
  })

  return (
    <>
      <PediatricHistoryPdfButton patientId={patientId} />
      <PediatricOdontogramSection
        patientId={patientId}
        canWrite={canWrite}
        encounterPicker={encounterPicker}
        anomalyCatalog={anomalyCatalogQuery.data ?? []}
      />
      <PerinatalHistorySection patientId={patientId} canWrite={canWrite} encounterId={encounterId} />
      <OralHabitsSection patientId={patientId} canWrite={canWrite} encounterId={encounterId} />
      <BehaviorMaturitySection
        patientId={patientId}
        canWrite={canWrite}
        encounterId={encounterId}
        characterCatalog={characterCatalogQuery.data ?? []}
      />
      <OcclusionSection
        patientId={patientId}
        canWrite={canWrite}
        encounterId={encounterId}
        terminalPlaneCatalog={terminalPlaneCatalogQuery.data ?? []}
      />
      <EruptionDentitionSection patientId={patientId} canWrite={canWrite} encounterId={encounterId} />
      <PediatricToothTreatmentPlanSection
        patientId={patientId}
        canWrite={canWrite}
        encounterId={encounterId}
      />
    </>
  )
}
